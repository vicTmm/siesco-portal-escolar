import base64
import hashlib
from conftest import authenticate


def audience(client, context):
    h, b = context
    guardians = client.get(b + "/guardians", headers=h).json()
    guardian = next(g for g in guardians if g["email"] == "familia@aurora.example.com")
    links = client.get(b + "/guardian-links", headers=h).json()
    sid = next(
        l["student_id"]
        for l in links
        if l["guardian_id"] == guardian["id"] and l["verified"]
    )
    enrollment = next(
        e
        for e in client.get(b + "/enrollments", headers=h).json()
        if e["student_id"] == sid
    )
    return sid, enrollment["academic_year"]


def test_authorization_receipts_and_family_scope(client, context):
    h, b = context
    sid, year = audience(client, context)
    r = client.post(
        b + "/notices",
        headers=h,
        json={
            "title": "Passeio escolar",
            "body": "Autoriza participação no passeio?",
            "kind": "authorization",
            "academic_year": year,
            "student_id": sid,
        },
    )
    assert r.status_code == 201, r.text
    nid = r.json()["id"]
    family = authenticate(client, "guardian@aurora.example.com")
    assert len(client.get(b + "/notices", headers=family).json()) == 1
    assert (
        client.post(
            b + f"/notices/{nid}/respond",
            headers=family,
            json={"student_id": sid, "answer": "yes"},
        ).status_code
        == 200
    )
    receipts = client.get(b + f"/notices/{nid}/receipts", headers=h).json()
    assert receipts[0]["read"] and receipts[0]["responses"][0]["answer"] == "yes"
    assert client.get(b + f"/notices/{nid}/receipts", headers=family).status_code == 403
    assert (
        client.post(
            b + f"/notices/{nid}/respond",
            headers=family,
            json={"student_id": sid, "answer": "withdraw"},
        ).status_code
        == 200
    )
    assert client.post(b + f"/notices/{nid}/archive", headers=h).status_code == 200
    assert client.get(b + "/notices", headers=family).json() == []


def test_document_private_download_public_hash_and_revocation(client, context):
    h, b = context
    sid, year = audience(client, context)
    r = client.post(
        b + "/documents",
        headers=h,
        json={"student_id": sid, "kind": "enrollment", "academic_year": year},
    )
    assert r.status_code == 201, r.text
    d = r.json()
    token = d["verification_url"].rsplit("/", 1)[1]
    public = client.get("/api/v1/verify-document/" + token)
    assert public.status_code == 200, public.text
    assert set(public.json()) == {
        "title",
        "institution",
        "issued_at",
        "valid",
        "sha256",
    }
    family = authenticate(client, "guardian@aurora.example.com")
    payload = client.get(b + f"/documents/{d['id']}/download", headers=family)
    assert payload.status_code == 200, payload.text
    pdf = base64.b64decode(payload.json()["base64"])
    assert (
        pdf.startswith(b"%PDF-")
        and hashlib.sha256(pdf).hexdigest() == public.json()["sha256"]
    )
    assert client.get(b + f"/documents/{d['id']}/download").status_code == 401
    assert (
        client.post(
            b + f"/documents/{d['id']}/revoke",
            headers=h,
            json={"reason": "Substituído por declaração atualizada"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/verify-document/" + token).json()["valid"] is False
    assert client.get("/api/v1/verify-document/" + "a" * 43).status_code == 404


def test_service_transitions_version_and_family_isolation(client, context):
    h, b = context
    sid, _ = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    r = client.post(
        b + "/services/tickets",
        headers=family,
        json={
            "title": "Dúvida sobre matrícula",
            "student_id": sid,
            "data": {
                "department": "Secretaria",
                "description": "Como atualizar endereço?",
            },
        },
    )
    assert r.status_code == 201, r.text
    record = r.json()
    path = b + "/service-records/" + record["id"] + "/transition"
    change = {
        "version": 1,
        "status": "in_progress",
        "note": "Secretaria iniciou atendimento",
    }
    assert client.post(path, headers=family, json=change).status_code == 403
    assert client.post(path, headers=h, json=change).status_code == 200
    assert client.post(path, headers=h, json=change).status_code == 409
    assert (
        client.get(
            b + "/service-records/" + record["id"] + "/events", headers=family
        ).json()[0]["data"]["to"]
        == "in_progress"
    )
    assert (
        client.post(
            b + "/services/finance",
            headers=family,
            json={"title": "Cobrança indevida", "student_id": sid, "data": {}},
        ).status_code
        == 403
    )


def test_health_restricted_and_family_read(client, context, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, _ = audience(client, context)
    r = client.post(
        b + "/services/health",
        headers=h,
        json={
            "title": "Cuidados de saúde",
            "student_id": sid,
            "data": {
                "allergies": "Restrição sintética",
                "care": "Contato antes de qualquer cuidado",
                "contact": "Responsável de teste",
            },
        },
    )
    assert r.status_code == 201, r.text
    secretary = authenticate(client, "secretary@aurora.example.com")
    assert client.get(b + "/services/health", headers=secretary).json() == []
    assert (
        client.get(
            b + "/service-records/" + r.json()["id"] + "/events", headers=secretary
        ).status_code
        == 403
    )
    user_id = client.get("/api/v1/me", headers=secretary).json()["id"]
    grant = {
        "student_id": sid,
        "user_id": user_id,
        "category": "health",
        "active": True,
    }
    assert (
        client.post(b + "/sensitive-grants", headers=h, json=grant).status_code == 200
    )
    assert len(client.get(b + "/services/health", headers=secretary).json()) == 1
    assert (
        client.post(
            b + "/sensitive-grants", headers=h, json={**grant, "active": False}
        ).status_code
        == 200
    )
    assert client.get(b + "/services/health", headers=secretary).json() == []
    from app.db import engine, tenant_context
    from sqlalchemy.orm import Session
    from app.models import ServiceRecord

    with Session(engine) as db, db.begin():
        tenant_context(db, b.rsplit("/", 1)[1])
        stored = db.get(ServiceRecord, r.json()["id"])
        assert set(stored.data) == {"encrypted"} and "Restrição" not in str(stored.data)
    family = authenticate(client, "guardian@aurora.example.com")
    assert (
        client.get(b + "/services/health", headers=family).json()[0]["data"][
            "allergies"
        ]
        == "Restrição sintética"
    )


def test_meeting_double_booking_and_overlap(client, context):
    from datetime import datetime, timedelta, timezone

    h, b = context
    sid, _ = audience(client, context)
    teacher = client.get(b + "/teachers", headers=h).json()[0]["id"]
    start = datetime.now(timezone.utc) + timedelta(days=10)
    data = {
        "teacher_id": teacher,
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(minutes=30)).isoformat(),
    }
    r = client.post(b + "/meetings", headers=h, json=data)
    assert r.status_code == 201, r.text
    assert client.post(b + "/meetings", headers=h, json=data).status_code == 409
    path = b + "/meetings/" + r.json()["id"] + "/book"
    family = authenticate(client, "guardian@aurora.example.com")
    data = {"student_id": sid, "version": 1}
    assert client.post(path, headers=family, json=data).status_code == 200
    assert client.post(path, headers=h, json=data).status_code == 409


def test_multiple_units_require_explicit_scope(client, context):
    h, b = context
    first = client.get("/api/v1/me", headers=h).json()["memberships"][0]
    r = client.post(b + "/units", headers=h, json={"name": "Unidade Norte"})
    assert r.status_code == 201, r.text
    memberships = client.get("/api/v1/me", headers=h).json()["memberships"]
    assert len(memberships) == 2
    assert client.get(b + "/students", headers=h).status_code == 409
    second = next(a for a in memberships if a["id"] != first["id"])
    assert (
        client.get(
            b + "/students", headers={**h, "X-Membership-Id": second["id"]}
        ).json()
        == []
    )
    assert client.get(
        b + "/students", headers={**h, "X-Membership-Id": first["id"]}
    ).json()
    family = authenticate(client, "guardian@aurora.example.com")
    assert (
        client.get(
            b + "/students", headers={**family, "X-Membership-Id": first["id"]}
        ).status_code
        == 404
    )


def test_timetable_resources_and_manual_correction(client, context):
    h, b = context
    assignments = client.get(b + "/assignments", headers=h).json()
    classes = client.get(b + "/classes", headers=h).json()
    year = next(
        c["academic_year"] for c in classes if c["id"] == assignments[0]["class_id"]
    )
    r = client.post(
        b + "/timetables",
        headers=h,
        json={
            "title": "Grade de teste",
            "academic_year": year,
            "periods_per_day": 2,
            "demands": [
                {
                    "assignment_id": assignments[0]["id"],
                    "room": "Sala A",
                    "periods": 3,
                    "blocked": [0],
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    rows = r.json()["rows"]
    assert len(rows) == 3
    assert len({(x["day"], x["period"]) for x in rows}) == 3
    assert all(not (x["day"] == 1 and x["period"] == 1) for x in rows)
    q = client.post(
        b + "/services/questions",
        headers=h,
        json={
            "title": "Questão sintética",
            "data": {
                "subject": "Matemática",
                "prompt": "Quanto é 2 + 2?",
                "options": "A) 4\nB) 5",
                "answer": "A",
                "explanation": "Soma de dois inteiros",
            },
        },
    ).json()
    client.post(
        b + "/service-records/" + q["id"] + "/transition",
        headers=h,
        json={"version": 1, "status": "ready", "note": "Revisada pelo professor"},
    )
    result = client.post(
        b + "/answer-sheets/correct",
        headers=h,
        json={"question_ids": [q["id"]], "answers": ["a"]},
    )
    assert result.status_code == 200 and result.json()["correct"] == 1


def test_attachment_authorization_follows_guardian_link(client, context):
    h, b = context
    sid, _ = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    record = client.post(
        b + "/services/renewals",
        headers=family,
        json={
            "title": "Rematrícula de teste",
            "student_id": sid,
            "data": {
                "academic_year": "2027",
                "contact": "Contato sintético",
                "address": "Endereço sintético",
                "notes": "Atualização cadastral",
            },
        },
    ).json()
    upload = client.post(
        b + "/service-records/" + record["id"] + "/attachments",
        headers=family,
        json={
            "filename": "teste.pdf",
            "base64": base64.b64encode(b"%PDF-1.7\nTeste").decode(),
        },
    )
    assert upload.status_code == 201, upload.text
    path = b + "/attachments/" + upload.json()["id"] + "/download"
    assert client.get(path, headers=family).status_code == 200
    link = next(
        l
        for l in client.get(b + "/guardian-links", headers=h).json()
        if l["student_id"] == sid
    )
    client.delete(b + "/guardian-links/" + link["id"], headers=h)
    assert client.get(path, headers=family).status_code == 403


def test_moments_require_current_image_consent(client, context):
    h, b = context
    sid, year = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    notice = client.post(
        b + "/notices",
        headers=h,
        json={
            "title": "Uso de imagem restrito",
            "purpose": "image",
            "body": "Autoriza a imagem no mural privado?",
            "kind": "authorization",
            "academic_year": year,
            "student_id": sid,
        },
    ).json()
    record = client.post(
        b + "/services/moments",
        headers=h,
        json={
            "title": "Momento sintético",
            "student_id": sid,
            "data": {
                "caption": "Atividade de demonstração",
                "consent_notice": notice["id"],
            },
        },
    )
    assert record.status_code == 201, record.text
    assert client.get(b + "/services/moments", headers=family).json() == []
    path = b + "/notices/" + notice["id"] + "/respond"
    assert (
        client.post(
            path, headers=family, json={"student_id": sid, "answer": "yes"}
        ).status_code
        == 200
    )
    assert len(client.get(b + "/services/moments", headers=family).json()) == 1
    assert (
        client.post(
            path, headers=family, json={"student_id": sid, "answer": "withdraw"}
        ).status_code
        == 200
    )
    assert client.get(b + "/services/moments", headers=family).json() == []
    assert (
        client.get(
            b + "/service-records/" + record.json()["id"] + "/attachments",
            headers=family,
        ).status_code
        == 404
    )


def test_new_resources_tenant_isolation_and_issued_content_guard(client, context):
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import DBAPIError
    from app.db import engine, tenant_context
    import pytest

    h, b = context
    sid, year = audience(client, context)
    n = client.post(
        b + "/notices",
        headers=h,
        json={
            "title": "Aviso protegido",
            "body": "Texto registrado para auditoria",
            "academic_year": year,
        },
    ).json()
    doc = client.post(
        b + "/documents",
        headers=h,
        json={"student_id": sid, "kind": "enrollment", "academic_year": year},
    ).json()
    other = authenticate(client, "director@horizonte.example.com")
    otherbase = (
        "/api/v1/institutions/"
        + client.get("/api/v1/me", headers=other).json()["memberships"][0][
            "institution_id"
        ]
    )
    assert (
        client.get(
            otherbase + "/documents/" + doc["id"] + "/download", headers=other
        ).status_code
        == 404
    )
    assert (
        client.get(
            otherbase + "/notices/" + n["id"] + "/receipts", headers=other
        ).status_code
        == 404
    )
    for table, identifier, change in [
        ("notices", n["id"], "body='Texto alterado'"),
        ("school_documents", doc["id"], "sha256='hash alterado'"),
    ]:
        with pytest.raises(DBAPIError), Session(engine) as db, db.begin():
            tenant_context(db, b.rsplit("/", 1)[1])
            db.execute(
                text(f"UPDATE {table} SET {change} WHERE id=:id"), {"id": identifier}
            )
    with engine.begin() as db:
        for table in [
            "notices",
            "school_documents",
            "service_records",
            "private_attachments",
            "meeting_slots",
        ]:
            assert db.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0


def test_library_reservation_prevents_second_checkout(client, context):
    h, b = context
    sid, _ = audience(client, context)
    book = client.post(
        b + "/services/books",
        headers=h,
        json={
            "title": "Livro fictício de teste",
            "data": {"author": "Autor sintético", "isbn": "Sem ISBN", "shelf": "A-001"},
        },
    ).json()
    payload = {
        "title": "Reserva do exemplar",
        "student_id": sid,
        "data": {
            "book": book["id"],
            "due_date": "2027-01-20",
            "notes": "Reserva de demonstração",
        },
    }
    family = authenticate(client, "guardian@aurora.example.com")
    first = client.post(b + "/services/library", headers=family, json=payload)
    assert first.status_code == 201 and first.json()["status"] == "reserved", first.text
    assert (
        client.post(b + "/services/library", headers=h, json=payload).status_code == 409
    )
    assert (
        client.post(
            b + "/service-records/" + book["id"] + "/transition",
            headers=h,
            json={"version": 1, "status": "archived", "note": "Arquivar exemplar"},
        ).status_code
        == 409
    )


def test_offline_sync_atomic_idempotent_and_conflicts(client, context):
    from test_learning import setup
    from uuid import uuid4

    h, b = context
    j, _, _ = setup(client, context)
    package = client.get(b + "/journals/" + j["id"] + "/offline-package", headers=h)
    assert package.status_code == 200, package.text
    assert package.json()["placements"] and package.json()["term_start"] == "2026-02-02"
    payload = {
        "key": str(uuid4()),
        "version": j["version"],
        "lessons": [
            {
                "date": "2026-03-03",
                "slot": 1,
                "content": "Plano guardado offline",
                "entries": [
                    {"student_id": s["id"], "status": "present"}
                    for s in package.json()["students"]
                ],
            }
        ],
    }
    path = b + "/journals/" + j["id"] + "/offline-sync"
    first = client.post(path, headers=h, json=payload)
    assert first.status_code == 200, first.text
    repeat = client.post(path, headers=h, json=payload)
    assert repeat.status_code == 200 and repeat.json()["already_applied"] is True
    assert len(client.get(b + "/journals/" + j["id"], headers=h).json()["lessons"]) == 1
    conflict = client.post(path, headers=h, json={**payload, "key": str(uuid4())})
    assert conflict.status_code == 409
    payload["key"] = str(uuid4())
    payload["version"] = first.json()["version"]
    payload["lessons"][0]["slot"] = 2
    payload["lessons"].append(
        {
            "date": "2025-01-01",
            "slot": 3,
            "content": "Data fora do período",
            "entries": payload["lessons"][0]["entries"],
        }
    )
    assert client.post(path, headers=h, json=payload).status_code == 422
    assert len(client.get(b + "/journals/" + j["id"], headers=h).json()["lessons"]) == 1


def test_pei_structured_goals_and_recorded_progress(client, context, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, _ = audience(client, context)
    plan = client.post(
        b + "/services/pei",
        headers=h,
        json={
            "title": "Plano sintético",
            "student_id": sid,
            "data": {
                "goals": "Leitura orientada",
                "adaptations": "Material adaptado",
                "strategies": "Apoio docente",
                "progress": "Avaliação inicial",
            },
        },
    ).json()
    goal = client.post(
        b + "/services/pei_goals",
        headers=h,
        json={
            "title": "Meta sintética",
            "student_id": sid,
            "data": {
                "pei_id": plan["id"],
                "goal": "Ler palavras do material preparado",
                "unit": "palavras",
                "target": "20",
                "current": "5",
                "due_date": "2026-12-20",
                "evidence": "Registro de observação docente",
            },
        },
    )
    assert goal.status_code == 201, goal.text
    rid = goal.json()["id"]
    family = authenticate(client, "guardian@aurora.example.com")
    assert client.get(b + "/services/pei_goals", headers=family).json() == []
    assert (
        client.post(
            b + "/service-records/" + rid + "/transition",
            headers=h,
            json={
                "version": 1,
                "status": "published",
                "note": "Meta revisada com a equipe",
            },
        ).status_code
        == 200
    )
    r = client.post(
        b + "/pei-goals/" + rid + "/progress",
        headers=h,
        json={
            "version": 2,
            "current": "12",
            "note": "Progresso observado na atividade de teste",
        },
    )
    assert r.status_code == 200 and r.json()["data"]["current"] == "12", r.text
    assert (
        client.post(
            b + "/pei-goals/" + rid + "/progress",
            headers=h,
            json={"version": 2, "current": "13", "note": "Tentativa com versão antiga"},
        ).status_code
        == 409
    )
    assert (
        client.get(b + "/services/pei_goals", headers=family).json()[0]["data"][
            "current"
        ]
        == "12"
    )


def test_medication_requires_specific_consent_and_prescription(
    client, context, monkeypatch
):
    from cryptography.fernet import Fernet
    from datetime import datetime, timedelta, timezone

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, year = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    consent = client.post(
        b + "/notices",
        headers=h,
        json={
            "title": "Autorização de medicação sintética",
            "body": "Autorização de teste, sem orientação clínica.",
            "kind": "authorization",
            "purpose": "medication",
            "academic_year": year,
            "student_id": sid,
        },
    ).json()
    r = client.post(
        b + "/services/medication",
        headers=family,
        json={
            "title": "Solicitação de teste",
            "student_id": sid,
            "data": {
                "instructions": "Texto sintético; nenhuma dose real informada.",
                "scheduled_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=1)
                ).isoformat(),
                "consent_notice": consent["id"],
                "notes": "Demonstração sem uso real",
            },
        },
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    path = b + "/service-records/" + rid + "/transition"
    change = {
        "version": 1,
        "status": "scheduled",
        "note": "Equipe revisou a solicitação",
    }
    assert client.post(path, headers=h, json=change).status_code == 409
    assert (
        client.post(
            b + "/notices/" + consent["id"] + "/respond",
            headers=family,
            json={"student_id": sid, "answer": "yes"},
        ).status_code
        == 200
    )
    assert client.post(path, headers=h, json=change).status_code == 409
    attachment = client.post(
        b + "/service-records/" + rid + "/attachments",
        headers=family,
        json={
            "filename": "prescricao-teste.pdf",
            "base64": base64.b64encode(b"%PDF-1.7\nDocumento de teste").decode(),
        },
    )
    assert attachment.status_code == 201, attachment.text
    assert client.post(path, headers=h, json=change).status_code == 200
    assert (
        client.post(
            b + "/notices/" + consent["id"] + "/respond",
            headers=family,
            json={"student_id": sid, "answer": "withdraw"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            path,
            headers=h,
            json={
                "version": 2,
                "status": "administered",
                "note": "Teste de bloqueio após retirada",
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            path,
            headers=family,
            json={
                "version": 2,
                "status": "cancelled",
                "note": "Responsável cancelou solicitação",
            },
        ).status_code
        == 200
    )


def test_wallet_idempotent_credit_limits_stock_and_refund(client, context, monkeypatch):
    from cryptography.fernet import Fernet
    from uuid import uuid4

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, _ = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    product = client.post(
        b + "/inventory",
        headers=h,
        json={
            "channel": "canteen",
            "code": "suco",
            "name": "Suco de teste",
            "price_cents": 500,
            "stock": 3,
            "tags": ["fruta"],
        },
    )
    assert product.status_code == 201, product.text
    credit = {
        "key": str(uuid4()),
        "amount_cents": 2000,
        "note": "Crédito manual fictício",
    }
    assert (
        client.post(
            b + "/wallets/" + sid + "/credit", headers=family, json=credit
        ).status_code
        == 403
    )
    r = client.post(b + "/wallets/" + sid + "/credit", headers=h, json=credit)
    assert r.status_code == 201, r.text
    assert (
        client.post(b + "/wallets/" + sid + "/credit", headers=h, json=credit).json()[
            "already_applied"
        ]
        is True
    )
    assert (
        client.get(b + "/wallets/" + sid, headers=family).json()["balance_cents"]
        == 2000
    )
    policy = {"version": 0, "daily_limit_cents": 700, "blocked_tags": ["fruta"]}
    assert (
        client.put(
            b + "/wallets/" + sid + "/policy", headers=family, json=policy
        ).status_code
        == 200
    )
    purchase = {
        "key": str(uuid4()),
        "channel": "canteen",
        "lines": [{"product_id": product.json()["id"], "quantity": 1, "version": 1}],
    }
    assert (
        client.post(
            b + "/wallets/" + sid + "/purchase", headers=h, json=purchase
        ).status_code
        == 409
    )
    policy.update(version=1, blocked_tags=[])
    assert (
        client.put(
            b + "/wallets/" + sid + "/policy", headers=family, json=policy
        ).status_code
        == 200
    )
    first = client.post(b + "/wallets/" + sid + "/purchase", headers=h, json=purchase)
    assert first.status_code == 201, first.text
    assert (
        client.post(
            b + "/wallets/" + sid + "/purchase", headers=h, json=purchase
        ).json()["already_applied"]
        is True
    )
    assert (
        client.post(
            b + "/wallets/" + sid + "/purchase",
            headers=h,
            json={**purchase, "key": str(uuid4())},
        ).status_code
        == 409
    )
    assert (
        client.get(b + "/wallets/" + sid, headers=family).json()["balance_cents"]
        == 1500
    )
    refund = {
        "key": str(uuid4()),
        "note": "Devolução fictícia registrada pela secretaria",
        "restock": True,
    }
    path = b + "/wallet-entries/" + first.json()["id"] + "/refund"
    assert client.post(path, headers=h, json=refund).status_code == 201
    assert client.post(path, headers=h, json=refund).json()["already_applied"] is True
    assert (
        client.post(path, headers=h, json={**refund, "key": str(uuid4())}).status_code
        == 409
    )
    assert client.get(b + "/inventory", headers=h).json()[0]["stock"] == 3
    assert (
        client.get(b + "/wallets/" + sid, headers=family).json()["balance_cents"]
        == 2000
    )


def test_pickup_one_use_code_and_current_consent(client, context, monkeypatch):
    from cryptography.fernet import Fernet
    from datetime import datetime, timedelta, timezone

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, year = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    notice = client.post(
        b + "/notices",
        headers=h,
        json={
            "title": "Retirada sintética por terceiro",
            "body": "Solicitação de teste com pessoa indicada pelo responsável.",
            "kind": "authorization",
            "purpose": "pickup",
            "academic_year": year,
            "student_id": sid,
        },
    ).json()
    client.post(
        b + "/notices/" + notice["id"] + "/respond",
        headers=family,
        json={"student_id": sid, "answer": "yes"},
    )
    r = client.post(
        b + "/pickups",
        headers=family,
        json={
            "student_id": sid,
            "person": "Pessoa fictícia autorizada",
            "relationship": "Familiar de teste",
            "valid_until": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat(),
            "consent_notice": notice["id"],
        },
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    path = b + "/pickups/" + rid + "/code"
    assert client.post(path, headers=family).status_code == 409
    assert (
        client.post(
            b + "/service-records/" + rid + "/attachments",
            headers=family,
            json={
                "filename": "documento-ficticio.pdf",
                "base64": base64.b64encode(
                    "%PDF-1.7\nDados sintéticos".encode()
                ).decode(),
            },
        ).status_code
        == 201
    )
    code = client.post(path, headers=family)
    assert code.status_code == 200
    payload = {"code": code.json()["code"], "identity_verified": False}
    assert client.post(b + "/pickups/check", headers=h, json=payload).status_code == 422
    assert (
        client.post(
            b + "/pickups/check",
            headers=family,
            json={**payload, "identity_verified": True},
        ).status_code
        == 403
    )
    assert (
        client.post(
            b + "/pickups/check", headers=h, json={**payload, "identity_verified": True}
        ).status_code
        == 200
    )
    assert (
        client.post(
            b + "/pickups/check", headers=h, json={**payload, "identity_verified": True}
        ).status_code
        == 409
    )
    card = client.post(b + "/school-cards/" + sid + "/issue", headers=family)
    assert card.status_code == 200
    checked = client.post(
        b + "/school-cards/check", headers=h, json={"code": card.json()["code"]}
    )
    assert checked.status_code == 200 and checked.json()["student_id"] == sid, (
        checked.text
    )
    entry = {"code": card.json()["code"], "identity_verified": False}
    path = b + "/school-cards/register-entry"
    assert client.post(path, headers=h, json=entry).status_code == 422
    entry["identity_verified"] = True
    assert client.post(path, headers=family, json=entry).status_code == 403
    first = client.post(path, headers=h, json=entry)
    assert first.status_code == 201, first.text
    assert client.post(path, headers=h, json=entry).json()["id"] == first.json()["id"]


def test_arrival_queue_geofence_and_manual_release(client, context, monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, _ = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    assert (
        client.put(
            b + "/pickup-location",
            headers=h,
            json={"latitude": 0, "longitude": 0, "radius_m": 500},
        ).status_code
        == 200
    )
    payload = {
        "student_id": sid,
        "vehicle": "Veículo fictício",
        "latitude": 1,
        "longitude": 1,
        "accuracy_m": 20,
    }
    assert (
        client.post(b + "/pickup-queue", headers=family, json=payload).status_code
        == 409
    )
    r = client.post(
        b + "/pickup-queue",
        headers=family,
        json={**payload, "latitude": 0, "longitude": 0},
    )
    assert r.status_code == 201, r.text
    assert (
        client.post(
            b + "/pickup-queue",
            headers=family,
            json={**payload, "latitude": 0, "longitude": 0},
        ).status_code
        == 409
    )
    rid = r.json()["id"]
    assert (
        client.post(
            b + "/service-records/" + rid + "/transition",
            headers=h,
            json={"version": 1, "status": "called", "note": "Chamada de demonstração"},
        ).status_code
        == 200
    )
    path = b + "/pickup-queue/" + rid + "/release"
    assert (
        client.post(
            path,
            headers=h,
            json={
                "version": 2,
                "identity_verified": False,
                "note": "Conferência de teste",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            path,
            headers=h,
            json={
                "version": 2,
                "identity_verified": True,
                "note": "Conferência de teste",
            },
        ).status_code
        == 200
    )
    assert client.get(b + "/pickup-queue", headers=family).json() == []


def test_medical_notices_are_private_and_encrypted(client, context, monkeypatch):
    from cryptography.fernet import Fernet
    from app.db import engine, tenant_context
    from sqlalchemy.orm import Session
    from app.models import Notice

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, year = audience(client, context)
    r = client.post(
        b + "/notices",
        headers=h,
        json={
            "title": "Autorização clínica de demonstração",
            "body": "Conteúdo médico sintético e restrito.",
            "kind": "authorization",
            "purpose": "medication",
            "academic_year": year,
            "student_id": sid,
        },
    )
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["body"] == "Conteúdo médico sintético e restrito."
    secretary = authenticate(client, "secretary@aurora.example.com")
    assert client.get(b + "/notices", headers=secretary).json() == []
    assert (
        client.get(b + "/notices/" + rid + "/receipts", headers=secretary).status_code
        == 404
    )
    with Session(engine) as db, db.begin():
        tenant_context(db, b.rsplit("/", 1)[1])
        n = db.get(Notice, rid)
        assert (
            n.body_encrypted and "sintético" not in n.body and "clínica" not in n.title
        )


def test_department_access_hours_and_message_notifications(client, context):
    h, b = context
    sid, _ = audience(client, context)
    department = client.post(
        b + "/services/office_hours",
        headers=h,
        json={
            "title": "Secretaria de demonstração",
            "data": {
                "department": "Secretaria",
                "weekdays": "1,2,3,4,5,6,7",
                "opens": "00:00",
                "closes": "23:59",
                "roles": "Diretor, Secretaria",
            },
        },
    )
    assert department.status_code == 201, department.text
    family = authenticate(client, "guardian@aurora.example.com")
    secretary = authenticate(client, "secretary@aurora.example.com")
    coordinator = authenticate(client, "coordinator@aurora.example.com")
    ticket = client.post(
        b + "/services/tickets",
        headers=family,
        json={
            "title": "Atendimento de teste",
            "student_id": sid,
            "data": {
                "department": "secretaria",
                "description": "Como atualizar o endereço?",
            },
        },
    ).json()
    rid = ticket["id"]
    assert (
        client.get(
            b + "/service-records/" + rid + "/events", headers=coordinator
        ).status_code
        == 403
    )
    assert client.get(b + "/services/tickets", headers=coordinator).json() == []
    assert (
        client.post(
            b + "/service-records/" + rid + "/comments",
            headers=secretary,
            json={"text": "A secretaria recebeu sua solicitação."},
        ).status_code
        == 201
    )
    notifications = client.get(b + "/notifications", headers=family)
    assert notifications.status_code == 200, notifications.text
    assert any(
        n["destination"] == "services:tickets" for n in notifications.json()["items"]
    )
    assert (
        client.get(
            b + "/service-records/" + rid + "/events", headers=family
        ).status_code
        == 200
    )
    assert not any(
        n["destination"] == "services:tickets"
        for n in client.get(b + "/notifications", headers=family).json()["items"]
    )


def test_student_read_does_not_count_as_guardian_confirmation(client, context):
    h, b = context
    student_headers = authenticate(client, "student@aurora.example.com")
    sid = client.get(b + "/portal", headers=student_headers).json()["students"][0]["id"]
    year = next(
        e["academic_year"]
        for e in client.get(b + "/enrollments", headers=h).json()
        if e["student_id"] == sid
    )
    n = client.post(
        b + "/notices",
        headers=h,
        json={
            "title": "Aviso de teste de leitura",
            "body": "Confirmação do responsável é distinta da leitura do aluno.",
            "academic_year": year,
            "student_id": sid,
        },
    ).json()
    assert (
        client.post(
            b + "/notices/" + n["id"] + "/respond",
            headers=student_headers,
            json={"student_id": sid},
        ).status_code
        == 200
    )
    receipts = client.get(b + "/notices/" + n["id"] + "/receipts", headers=h).json()
    assert receipts[0]["read"] is False and receipts[0]["any_read"] is True
    family = authenticate(client, "guardian@aurora.example.com")
    assert (
        client.post(
            b + "/notices/" + n["id"] + "/respond",
            headers=family,
            json={"student_id": sid},
        ).status_code
        == 200
    )
    assert (
        client.get(b + "/notices/" + n["id"] + "/receipts", headers=h).json()[0]["read"]
        is True
    )


def test_negotiation_preserves_total_and_restructures_once(client, context):

    h, b = context
    sid, _ = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    source = client.post(
        b + "/services/finance",
        headers=h,
        json={
            "title": "Conta de demonstração",
            "student_id": sid,
            "data": {
                "amount_cents": "1375",
                "due_date": "2030-01-01",
                "reference": "Referência de teste",
                "notes": "Conta sintética",
            },
        },
    ).json()
    payload = {
        "student_id": sid,
        "receivable_ids": [source["id"]],
        "installments": 3,
        "first_due": "2030-01-31",
    }
    quote = client.post(b + "/negotiations/simulate", headers=family, json=payload)
    assert quote.status_code == 200, quote.text
    assert sum(p["amount_cents"] for p in quote.json()["schedule"]) == 1375
    assert quote.json()["schedule"][1]["due_date"] == "2030-02-28"
    proposal = client.post(
        b + "/negotiations/propose",
        headers=family,
        json={**payload, "note": "Proposta sintética de parcelamento"},
    ).json()
    rid = proposal["id"]
    path = b + "/service-records/" + rid + "/transition"
    assert (
        client.post(
            path,
            headers=family,
            json={"version": 1, "status": "review", "note": "Análise solicitada"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            path,
            headers=h,
            json={
                "version": 1,
                "status": "review",
                "note": "Secretaria iniciou a análise",
            },
        ).status_code
        == 200
    )
    approved = client.post(
        path,
        headers=h,
        json={
            "version": 2,
            "status": "approved",
            "note": "Condições aprovadas pela escola",
        },
    )
    assert approved.status_code == 200, approved.text
    assert len(approved.json()["proposal"]["created_receivables"]) == 3
    finance = client.get(b + "/services/finance", headers=h).json()
    assert (
        next(r for r in finance if r["id"] == source["id"])["status"] == "restructured"
    )
    assert (
        sum(int(r["data"]["amount_cents"]) for r in finance if r["status"] == "pending")
        == 1375
    )
    assert (
        client.post(
            path,
            headers=h,
            json={"version": 2, "status": "approved", "note": "Tentativa duplicada"},
        ).status_code
        == 409
    )


def test_calendar_published_audience_and_academic_permissions(client, context):
    h, b = context
    payload = {
        "title": "Evento escolar de demonstração",
        "data": {
            "starts_at": "2030-03-01T10:00:00-03:00",
            "ends_at": "2030-03-01T11:00:00-03:00",
            "location": "Escola sintética",
            "description": "Encontro de demonstração",
        },
    }
    secretary = authenticate(client, "secretary@aurora.example.com")
    assert (
        client.post(
            b + "/services/calendar", headers=secretary, json=payload
        ).status_code
        == 403
    )
    r = client.post(b + "/services/calendar", headers=h, json=payload)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    family = authenticate(client, "guardian@aurora.example.com")
    assert client.get(b + "/services/calendar", headers=family).json() == []
    assert (
        client.post(
            b + "/service-records/" + rid + "/transition",
            headers=h,
            json={
                "version": 1,
                "status": "published",
                "note": "Evento revisado pela coordenação",
            },
        ).status_code
        == 200
    )
    assert len(client.get(b + "/services/calendar", headers=family).json()) == 1
    assert (
        client.get(
            b + "/service-records/" + rid + "/events", headers=family
        ).status_code
        == 403
    )
    student = authenticate(client, "student@aurora.example.com")
    assert (
        client.post(
            b + "/service-records/" + rid + "/comments",
            headers=student,
            json={"text": "Tentativa de alterar conteúdo público"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            b + "/service-records/" + rid + "/attachments",
            headers=student,
            json={
                "filename": "teste.pdf",
                "base64": base64.b64encode(b"%PDF-1.7").decode(),
            },
        ).status_code
        == 403
    )


def test_exam_snapshots_keep_answers_out_of_student_pdf(client, context):
    from pypdf import PdfReader
    import io

    h, b = context
    q = client.post(
        b + "/services/questions",
        headers=h,
        json={
            "title": "RESPOSTA INTERNA: alternativa A",
            "data": {
                "subject": "Matemática",
                "prompt": "Considere α ∈ ℝ e θ ≤ √25. Assinale a alternativa.",
                "options": "A) Verdadeira\nB) Falsa",
                "answer": "A",
                "explanation": "JUSTIFICATIVA RESERVADA AO DOCENTE",
            },
        },
    ).json()
    assert (
        client.post(
            b + "/service-records/" + q["id"] + "/transition",
            headers=h,
            json={"version": 1, "status": "ready", "note": "Questão revisada"},
        ).status_code
        == 200
    )
    exam = client.post(
        b + "/exams",
        headers=h,
        json={
            "title": "Avaliação de demonstração",
            "instructions": "Leia as questões antes de responder.",
            "question_ids": [q["id"]],
        },
    )
    assert exam.status_code == 201, exam.text
    rid = exam.json()["id"]
    paper = client.get(b + "/exams/" + rid + "/pdf", headers=h)
    key = client.get(b + "/exams/" + rid + "/pdf?answer_key=true", headers=h)
    assert paper.status_code == 200, paper.text

    def text(response):
        return "\n".join(
            page.extract_text()
            for page in PdfReader(
                io.BytesIO(base64.b64decode(response.json()["base64"]))
            ).pages
        )

    assert "JUSTIFICATIVA RESERVADA" not in text(paper)
    assert "RESPOSTA INTERNA" not in text(paper)
    assert "α ∈ ℝ" in text(paper) and "JUSTIFICATIVA RESERVADA" in text(key)
    student = authenticate(client, "student@aurora.example.com")
    assert (
        client.get(
            b + "/exams/" + rid + "/pdf?answer_key=true", headers=student
        ).status_code
        == 403
    )
    assert (
        client.post(
            b + "/service-records/" + q["id"] + "/transition",
            headers=h,
            json={
                "version": 2,
                "status": "archived",
                "note": "Questão substituída no banco",
            },
        ).status_code
        == 200
    )
    result = client.post(
        b + "/exams/" + rid + "/correct", headers=h, json={"answers": ["a"]}
    )
    assert result.status_code == 200 and result.json()["correct"] == 1


def test_unsigned_contract_template_and_guardian_download(client, context):
    from pypdf import PdfReader
    import io

    h, b = context
    sid, year = audience(client, context)
    template = client.post(
        b + "/services/contract_templates",
        headers=h,
        json={
            "title": "Modelo sintético de minuta",
            "data": {
                "clauses": "Escola: {{escola}}. Aluno: {{aluno}}. Responsável: {{responsavel}}. Ano: {{ano_letivo}}. Valor informado: {{mensalidade}}. Texto fictício para revisão.",
                "notes": "Não contém cláusulas jurídicas reais.",
            },
        },
    )
    assert template.status_code == 201, template.text
    rid = template.json()["id"]
    assert (
        client.post(
            b + "/service-records/" + rid + "/transition",
            headers=h,
            json={
                "version": 1,
                "status": "published",
                "note": "Modelo de demonstração revisado",
            },
        ).status_code
        == 200
    )
    guardian = next(
        g
        for g in client.get(b + "/guardians", headers=h).json()
        if g["email"] == "familia@aurora.example.com"
    )
    issued = client.post(
        b + "/contracts/draft",
        headers=h,
        json={
            "template_id": rid,
            "student_id": sid,
            "guardian_id": guardian["id"],
            "academic_year": year,
            "monthly_cents": 123456,
        },
    )
    assert issued.status_code == 201, issued.text
    did = issued.json()["id"]
    family = authenticate(client, "guardian@aurora.example.com")
    pdf = client.get(b + "/documents/" + did + "/download", headers=family)
    assert pdf.status_code == 200
    text = "\n".join(
        p.extract_text()
        for p in PdfReader(io.BytesIO(base64.b64decode(pdf.json()["base64"]))).pages
    )
    assert (
        "MINUTA SEM ASSINATURA" in text
        and "R$ 1.234,56" in text
        and "{{aluno}}" not in text
    )
    token = issued.json()["verification_url"].rsplit("/", 1)[1]
    assert (
        client.get("/api/v1/verify-document/" + token).json()["signature"] == "unsigned"
    )
    student = authenticate(client, "student@aurora.example.com")
    assert (
        client.get(b + "/documents/" + did + "/download", headers=student).status_code
        == 403
    )


def test_revoking_last_staff_profile_removes_clinical_grant(
    client, context, monkeypatch
):
    from cryptography.fernet import Fernet
    from app.db import engine, tenant_context
    from app.models import SensitiveGrant
    from sqlalchemy.orm import Session
    from sqlalchemy import select

    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    sid, _ = audience(client, context)
    family = authenticate(client, "guardian@aurora.example.com")
    uid = client.get("/api/v1/me", headers=family).json()["id"]
    profile = client.post(
        b + "/accounts",
        headers=h,
        json={
            "name": "Responsável com função na equipe",
            "email": "guardian@aurora.example.com",
            "password": "SenhaSintetica123!",
            "role": "secretary",
        },
    )
    assert profile.status_code == 201, profile.text
    grant = {"student_id": sid, "user_id": uid, "category": "health", "active": True}
    assert (
        client.post(b + "/sensitive-grants", headers=h, json=grant).status_code == 200
    )
    assert (
        client.delete(b + "/accounts/" + profile.json()["id"], headers=h).status_code
        == 204
    )
    assert len(client.get("/api/v1/me", headers=family).json()["memberships"]) == 1
    with Session(engine) as db, db.begin():
        tenant_context(db, b.rsplit("/", 1)[1])
        stored = db.scalar(select(SensitiveGrant).where(SensitiveGrant.user_id == uid))
        assert stored is not None and stored.active is False

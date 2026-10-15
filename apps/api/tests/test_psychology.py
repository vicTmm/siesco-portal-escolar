import base64
from datetime import datetime, timedelta, timezone
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from app.db import engine, tenant_context
from app.models import ServiceRecord, ServiceEvent, PrivateAttachment
from conftest import authenticate


@pytest.fixture
def clinical(client, context, monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    p = authenticate(client, "psychologist@aurora.example.com")
    sid = client.get(b + "/psychology/students", headers=p).json()[0]["id"]
    data = {
        "student_id": sid,
        "occurred_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "kind": "initial",
        "observations": "Observação confidencial sintética",
        "analysis": "Análise reservada de demonstração",
        "plan": "Acompanhamento individual",
        "next_visit": None,
    }
    r = client.post(b + "/psychology", headers=p, json=data)
    assert r.status_code == 201, r.text
    return h, b, p, r.json(), data


def test_psychology_encrypted_director_read_author_only_write(client, clinical):
    h, b, p, r, _ = clinical
    assert (
        client.get(b + "/psychology", headers=h).json()[0]["data"]["analysis"]
        == "Análise reservada de demonstração"
    )
    assert (
        client.post(b + "/psychology", headers=h, json=clinical[-1]).status_code == 403
    )
    path = b + "/psychology/" + r["id"] + "/notes"
    note = {"text": "Complemento e retificação preservados", "version": 1}
    assert client.post(path, headers=h, json=note).status_code == 403
    assert client.post(path, headers=p, json=note).status_code == 201
    assert client.post(path, headers=p, json=note).status_code == 409
    upload = client.post(
        b + "/service-records/" + r["id"] + "/attachments",
        headers=p,
        json={
            "filename": "analise.pdf",
            "base64": base64.b64encode(b"%PDF-1.7\nSintetico").decode(),
        },
    )
    assert upload.status_code == 201, upload.text
    assert (
        client.get(
            b + "/attachments/" + upload.json()["id"] + "/download", headers=h
        ).status_code
        == 200
    )
    assert (
        client.post(
            b + "/service-records/" + r["id"] + "/attachments",
            headers=h,
            json={
                "filename": "direcao.pdf",
                "base64": base64.b64encode(b"%PDF-1.7\nSintetico").decode(),
            },
        ).status_code
        == 403
    )
    assert (
        client.get(b + "/service-records/" + r["id"] + "/events", headers=h).json()[0][
            "data"
        ]["text"]
        == note["text"]
    )
    with Session(engine) as db, db.begin():
        tenant_context(db, b.rsplit("/", 1)[1])
        stored = db.get(ServiceRecord, r["id"])
        assert set(stored.data) == {"encrypted"} and "Análise" not in str(stored.data)
        from sqlalchemy import update
        from sqlalchemy.exc import DBAPIError

        with pytest.raises(DBAPIError), db.begin_nested():
            db.execute(
                update(ServiceRecord)
                .where(ServiceRecord.id == r["id"])
                .values(title="Conteúdo indevidamente alterado")
            )
        event = db.query(ServiceEvent).filter(ServiceEvent.record_id == r["id"]).one()
        assert set(event.data) == {"encrypted"} and "Complemento" not in str(event.data)
        a = db.get(PrivateAttachment, upload.json()["id"])
        assert not a.content.startswith(b"%PDF-")


@pytest.mark.parametrize(
    "role", ["secretary", "coordinator", "teacher", "guardian", "student"]
)
def test_psychology_denies_unrelated_profiles_all_paths(client, clinical, role):
    _, b, _, r, _ = clinical
    other = authenticate(client, role + "@aurora.example.com")
    assert client.get(b + "/psychology", headers=other).status_code == 403
    assert client.get(b + "/psychology/students", headers=other).status_code == 403
    assert (
        client.get(
            b + "/service-records/" + r["id"] + "/events", headers=other
        ).status_code
        == 403
    )
    assert (
        client.get(
            b + "/service-records/" + r["id"] + "/attachments", headers=other
        ).status_code
        == 403
    )
    assert client.post(
        b + "/service-records/" + r["id"] + "/comments",
        headers=other,
        json={"text": "Não pode acessar"},
    ).status_code in {403, 405}
    assert (
        "Observação confidencial"
        not in client.get(b + "/notifications", headers=other).text
    )


def test_psychology_other_school_author_and_revocation(client, clinical):
    h, b, p, r, _ = clinical
    school = authenticate(client, "director@horizonte.example.com")
    otherbase = (
        "/api/v1/institutions/"
        + client.get("/api/v1/me", headers=school).json()["memberships"][0][
            "institution_id"
        ]
    )
    assert (
        client.get(
            otherbase + "/service-records/" + r["id"] + "/events", headers=school
        ).status_code
        == 404
    )
    account = client.post(
        b + "/accounts",
        headers=h,
        json={
            "name": "Outro profissional",
            "email": "otherpsy@example.com",
            "password": "Psicologia123!",
            "role": "psychologist",
        },
    )
    assert account.status_code == 201, account.text
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "otherpsy@example.com", "password": "Psicologia123!"},
    ).json()["access_token"]
    other = {"Authorization": "Bearer " + token}
    assert client.get(b + "/psychology", headers=other).json() == []
    assert (
        client.get(
            b + "/service-records/" + r["id"] + "/events", headers=other
        ).status_code
        == 404
    )
    profile = client.get("/api/v1/me", headers=p).json()["memberships"][0]
    assert client.delete(b + "/accounts/" + profile["id"], headers=h).status_code == 204
    assert client.get(b + "/psychology", headers=p).status_code == 404
    assert client.get(b + "/psychology", headers=h).status_code == 200

    from app.seed import seed

    seed()
    assert client.get(b + "/psychology", headers=p).status_code == 404

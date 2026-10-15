from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db import engine, tenant_context
from app import models as m
from conftest import authenticate


def test_authentication_logout_expiration(client):
    assert client.get("/api/v1/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "director@aurora.example.com", "password": "wrong"}).status_code == 401
    headers = authenticate(client)
    assert client.get("/api/v1/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/me", headers=headers).status_code == 401
    headers = authenticate(client)
    with Session(engine) as db, db.begin():
        session = db.scalar(select(m.LoginSession))
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_login_rate_limit(client):
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json={"email": "unknown@demo.example.com", "password": "wrong"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "unknown@demo.example.com", "password": "wrong"}).status_code == 429


def test_platform_bootstrap_and_no_school_access(client, context):
    headers, base = context
    assert client.get("/api/v1/platform/institutions", headers=headers).status_code == 403
    admin = authenticate(client, "admin@demo.example.com")
    assert client.get(base + "/students", headers=admin).status_code == 404
    response = client.post("/api/v1/platform/institutions", headers=admin, json={"name": "Instituição Fictícia", "slug": "ficticia", "director_name": "Diretor Teste", "director_email": "director@ficticia.example.com", "director_password": "SenhaFicticia123!"})
    assert response.status_code == 201, response.text
    login = client.post("/api/v1/auth/login", json={"email": "director@ficticia.example.com", "password": "SenhaFicticia123!"})
    new_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/api/v1/institutions/" + response.json()["id"] + "/students", headers=new_headers).json() == []


@pytest.mark.parametrize("role,resource,status", [("secretary", "students", 201), ("coordinator", "students", 403), ("teacher", "students", 403), ("student", "students", 403), ("guardian", "students", 403)])
def test_write_permissions(client, context, role, resource, status):
    _, base = context
    headers = authenticate(client, role + "@aurora.example.com")
    assert client.post(base + "/" + resource, headers=headers, json={"name": "Aluno Fictício", "birth_date": "2015-01-01"}).status_code == status


@pytest.mark.parametrize("resource", ["students", "guardians", "teachers", "subjects", "classes", "guardian-links", "assignments", "enrollments", "dashboard", "accounts", "portal"])
def test_cross_tenant_access(client, context, resource):
    headers, base = context
    other = authenticate(client, "director@horizonte.example.com")
    assert client.get(base + "/" + resource, headers=other).status_code == 404


def test_catalog_operations_validation_and_audit(client, context):
    headers, base = context
    cases = [("students", {"name": "Novo Aluno Fictício", "birth_date": "2016-01-01"}),
             ("guardians", {"name": "Família Fictícia", "email": "nova@demo.example.com", "phone": ""}),
             ("teachers", {"name": "Docente Fictício", "email": "novo@demo.example.com"}),
             ("subjects", {"name": "História", "code": "HIS"}),
             ("classes", {"name": "Turma Teste", "academic_year": 2026, "grade_level": "7º ano", "shift": "morning", "capacity": 20})]
    for resource, payload in cases:
        response = client.post(base + "/" + resource, json=payload, headers=headers)
        assert response.status_code == 201, response.text
        payload["name"] += " Atualizado"
        updated = client.put(base + "/" + resource + "/" + response.json()["id"], json=payload, headers=headers)
        assert updated.status_code == 200, updated.text
        assert updated.json()["name"] == payload["name"]
    assert client.post(base + "/students", headers=headers, json={"name": "Teste", "birth_date": "2200-01-01"}).status_code == 422
    assert client.post(base + "/students", headers=headers, json={"name": "Teste", "birth_date": "2010-01-01", "institution_id": "injection"}).status_code == 422
    assert client.post(base + "/subjects", headers=headers, json={"name": "Duplicada", "code": "HIS"}).status_code == 409
    assert client.get(base + "/students?limit=1000", headers=headers).status_code == 422
    assert len(client.get(base + "/students?q=Atualizado", headers=headers).json()) == 1
    with Session(engine) as db, db.begin():
        tenant_context(db, base.split("/")[-1])
        assert len(db.scalars(select(m.AuditEvent)).all()) == 10


def test_links_assignments_and_scoped_portals(client, context):
    headers, base = context
    guardian = authenticate(client, "guardian@aurora.example.com")
    teacher = authenticate(client, "teacher@aurora.example.com")
    student = authenticate(client, "student@aurora.example.com")
    for auth, count in [(guardian, 1), (student, 1), (teacher, 2)]:
        response = client.get(base + "/portal", headers=auth)
        assert len(response.json()["students"]) == count
        assert set(response.json()["students"][0]) == {"id", "name"}
        assert client.get(base + "/students", headers=auth).status_code == 403
    link = client.get(base + "/guardian-links", headers=headers).json()[0]
    assert client.delete(base + "/guardian-links/" + link["id"], headers=headers).status_code == 204
    assert client.get(base + "/portal", headers=guardian).json()["students"] == []
    updated = client.put(base + "/guardian-links/" + link["id"], headers=headers, json={"student_id": link["student_id"], "guardian_id": link["guardian_id"], "relationship": "Responsável", "verified": True})
    assert updated.status_code == 200
    assert len(client.get(base + "/portal", headers=guardian).json()["students"]) == 1
    client.delete(base + "/guardian-links/" + link["id"], headers=headers)
    students = client.get(base + "/students", headers=headers).json()
    new_link = client.post(base + "/guardian-links", headers=headers, json={"student_id": students[1]["id"], "guardian_id": link["guardian_id"], "relationship": "Responsável", "verified": False})
    assert new_link.status_code == 201
    assert client.get(base + "/portal", headers=guardian).json()["students"] == []
    group = client.get(base + "/classes", headers=headers).json()[1]
    subject = client.get(base + "/subjects", headers=headers).json()[0]
    teacher_record = client.get(base + "/teachers", headers=headers).json()[0]
    response = client.post(base + "/assignments", headers=headers, json={"class_id": group["id"], "subject_id": subject["id"], "teacher_id": teacher_record["id"]})
    assert response.status_code == 201
    assert len(client.get(base + "/portal", headers=teacher).json()["students"]) == 4


def test_enrollment_duplicate_capacity_cancel(client, context):
    headers, base = context
    assert client.post(base + "/academic-years", headers=headers, json={"name": "2027", "year": 2027, "start_date": "2027-02-01", "end_date": "2027-12-20"}).status_code == 201
    group = client.post(base + "/classes", headers=headers, json={"name": "Uma vaga", "academic_year": 2027, "grade_level": "7º ano", "shift": "morning", "capacity": 1}).json()
    students = client.get(base + "/students", headers=headers).json()
    payload = {"student_id": students[0]["id"], "class_id": group["id"]}
    response = client.post(base + "/enrollments", headers=headers, json=payload)
    assert response.status_code == 201
    assert client.post(base + "/enrollments", headers=headers, json=payload).status_code == 409
    assert client.post(base + "/enrollments", headers=headers, json={**payload, "student_id": students[1]["id"]}).status_code == 409
    assert client.post(base + "/enrollments/" + response.json()["id"] + "/move", headers=headers, json={"action": "cancel", "date": "2027-03-01", "reason": "Cancelamento solicitado pela família."}).json()["status"] == "cancelled"
    assert client.post(base + "/enrollments", headers=headers, json={**payload, "student_id": students[1]["id"]}).status_code == 201


def test_concurrent_enrollment_never_exceeds_capacity(client, context):
    headers, base = context
    assert client.post(base + "/academic-years", headers=headers, json={"name": "2027", "year": 2027, "start_date": "2027-02-01", "end_date": "2027-12-20"}).status_code == 201
    group = client.post(base + "/classes", headers=headers, json={"name": "Concorrência", "academic_year": 2027, "grade_level": "7º ano", "shift": "morning", "capacity": 1}).json()
    students = client.get(base + "/students", headers=headers).json()
    def enroll(student):
        return client.post(base + "/enrollments", headers=headers, json={"student_id": student["id"], "class_id": group["id"]}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(enroll, students[:2])) == [201, 409]


def test_foreign_ids_rejected(client, context):
    headers, base = context
    other_headers = authenticate(client, "director@horizonte.example.com")
    tenant = client.get("/api/v1/me", headers=other_headers).json()["memberships"][0]["institution_id"]
    foreign = client.get("/api/v1/institutions/" + tenant + "/students", headers=other_headers).json()[0]
    group = client.get(base + "/classes", headers=headers).json()[0]
    assert client.post(base + "/enrollments", headers=headers, json={"student_id": foreign["id"], "class_id": group["id"]}).status_code == 404
    assert client.put(base + "/students/" + foreign["id"], headers=headers, json={"name": "Intruso", "birth_date": "2010-01-01"}).status_code == 404


def test_account_create_and_immediate_revocation(client, context):
    headers, base = context
    response = client.post(base + "/accounts", headers=headers, json={"name": "Secretaria Teste", "email": "access@demo.example.com", "password": "Ficticia123456!", "role": "secretary"})
    assert response.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": "access@demo.example.com", "password": "Ficticia123456!"})
    auth = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get(base + "/students", headers=auth).status_code == 200
    assert client.delete(base + "/accounts/" + response.json()["id"], headers=headers).status_code == 204
    assert client.get(base + "/students", headers=auth).status_code == 404


def test_rls_real_postgres_context_reset_and_write_check(client, context):
    headers, base = context
    tenant = base.split("/")[-1]
    with engine.connect() as db:
        with db.begin():
            role = db.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
            assert role == (False, False)
            assert db.execute(text("SELECT count(*) FROM students")).scalar() == 0
            db.execute(text("SELECT set_config('app.institution_id', :id, true)"), {"id": tenant})
            assert db.execute(text("SELECT count(*) FROM students")).scalar() == 4
        with db.begin():
            assert db.execute(text("SELECT count(*) FROM students")).scalar() == 0
        with pytest.raises(DBAPIError), db.begin():
            db.execute(text("INSERT INTO students (id,institution_id,school_id,name,birth_date) VALUES ('x','foreign','x','Invalid','2010-01-01')"))
    with Session(engine) as db, db.begin():
        tenant_context(db, tenant)
        school = db.scalar(select(m.School))
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM audit_events"))


def test_openapi_and_dashboard(client, context):
    headers, base = context
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/v1/institutions/{institution_id}/enrollments" in schema.json()["paths"]
    response = client.get(base + "/dashboard", headers=headers)
    assert response.json()["counts"]["students"] == 4
    assert response.json()["counts"]["enrollments"] == 4


@pytest.mark.parametrize("resource,payload", [
    ("subjects", {"name": "História", "code": "HIS"}),
    ("teachers", {"name": "Docente", "email": "extra@example.com"}),
    ("classes", {"name": "Turma", "academic_year": 2026, "grade_level": "7º ano", "shift": "morning", "capacity": 20}),
    ("accounts", {"name": "Intruso", "email": "intruso@example.com", "password": "LongPassword123!", "role": "director"})])
def test_secretary_cannot_write_academic_or_grant_roles(client, context, resource, payload):
    _, base = context
    headers = authenticate(client, "secretary@aurora.example.com")
    assert client.post(base + "/" + resource, json=payload, headers=headers).status_code == 403


def test_seed_idempotence(client, context):
    from app.seed import seed
    seed()
    headers, base = context
    assert client.get(base + "/dashboard", headers=headers).json()["counts"]["students"] == 4


def test_database_composite_fk_rejects_cross_tenant_student(client, context):
    _, base = context
    other = authenticate(client, "director@horizonte.example.com")
    foreign_tenant = client.get("/api/v1/me", headers=other).json()["memberships"][0]["institution_id"]
    foreign_student = client.get(f"/api/v1/institutions/{foreign_tenant}/students", headers=other).json()[0]["id"]
    with Session(engine) as db, db.begin():
        tenant_context(db, base.split("/")[-1])
        group = db.scalar(select(m.ClassGroup))
        db.add(m.Enrollment(institution_id=group.institution_id, school_id=group.school_id, student_id=foreign_student, class_id=group.id, academic_year=group.academic_year))
        with pytest.raises(DBAPIError):
            db.flush()

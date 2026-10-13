from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app import models as m
from app.db import engine, tenant_context
from conftest import authenticate


YEAR = {"name": "Calendário 2027", "year": 2027, "start_date": "2027-02-01", "end_date": "2027-12-20"}
CURRICULUM = {"name": "Ensino fundamental", "code": "EF7", "grade_level": "7º ano", "version": 1}


def post(client, context, path, payload):
    headers, base = context
    response = client.post(base + "/" + path, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def curriculum_with_subject(client, context):
    headers, base = context
    curriculum = post(client, context, "curricula", CURRICULUM)
    subject = client.get(base + "/subjects", headers=headers).json()[0]
    component = post(client, context, "curriculum-subjects", {"curriculum_id": curriculum["id"], "subject_id": subject["id"], "workload_hours": 120})
    return curriculum, component


def test_calendar_dates_terms_and_history(client, context):
    headers, base = context
    assert client.post(base + "/academic-years", headers=headers, json={**YEAR, "end_date": "2027-01-01"}).status_code == 422
    year = post(client, context, "academic-years", YEAR)
    assert not year["needs_review"]
    assert client.post(base + "/academic-years", headers=headers, json=YEAR).status_code == 409
    term = {"name": "1º bimestre", "academic_year_id": year["id"], "sequence": 1, "start_date": "2027-02-01", "end_date": "2027-04-15"}
    first = post(client, context, "academic-terms", term)
    assert client.post(base + "/academic-terms", headers=headers, json={**term, "name": "Sobreposto", "sequence": 2, "start_date": "2027-04-15", "end_date": "2027-06-01"}).status_code == 409
    assert client.post(base + "/academic-terms", headers=headers, json={**term, "name": "Fora do ano", "sequence": 3, "start_date": "2027-01-01"}).status_code == 422
    second = post(client, context, "academic-terms", {**term, "name": "2º bimestre", "sequence": 2, "start_date": "2027-04-16", "end_date": "2027-06-30"})
    assert client.post(base + "/academic-terms", headers=headers, json={**term, "name": "Sequência inválida", "sequence": 1, "start_date": "2027-07-01", "end_date": "2027-08-01"}).status_code == 409
    assert client.put(base + "/academic-years/" + year["id"], headers=headers, json={**YEAR, "end_date": "2027-06-01"}).status_code == 409
    assert client.put(base + "/academic-years/" + year["id"], headers=headers, json={**YEAR, "year": 2028}).status_code == 409
    assert client.put(base + "/academic-terms/" + second["id"], headers=headers, json={**term, "name": "2º bimestre", "sequence": 2, "start_date": "2027-04-10", "end_date": "2027-06-30"}).status_code == 409
    assert client.put(base + "/academic-terms/" + first["id"], headers=headers, json={**term, "name": "Primeiro período"}).status_code == 200
    with Session(engine) as db, db.begin():
        tenant_context(db, year["institution_id"])
        actions = db.scalars(select(m.AuditEvent.action)).all()
        assert actions.count("academic_years.create") == 1
        assert actions.count("academic_terms.create") == 2
        assert actions.count("academic_terms.update") == 1


def test_concurrent_overlapping_terms_only_one_succeeds(client, context):
    headers, base = context
    year = post(client, context, "academic-years", YEAR)
    def add(sequence):
        return client.post(base + "/academic-terms", headers=headers, json={"name": f"Período {sequence}", "academic_year_id": year["id"], "sequence": sequence, "start_date": "2027-02-01", "end_date": "2027-05-01"}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(add, [1, 2])) == [201, 409]


def test_curriculum_publication_and_new_version_preserve_history(client, context):
    headers, base = context
    curriculum, component = curriculum_with_subject(client, context)
    path = base + "/curricula/" + curriculum["id"]
    assert client.post(base + "/curricula", headers=headers, json=CURRICULUM).status_code == 409
    assert client.put(path, headers=headers, json={**CURRICULUM, "version": 2}).status_code == 409
    assert client.post(path + "/publish", headers=headers).json()["status"] == "published"
    assert client.post(path + "/publish", headers=headers).status_code == 200
    assert client.put(path, headers=headers, json={**CURRICULUM, "name": "Mudança indevida"}).status_code == 409
    payload = {key: component[key] for key in ["curriculum_id", "subject_id", "workload_hours"]}
    assert client.put(base + "/curriculum-subjects/" + component["id"], headers=headers, json={**payload, "workload_hours": 200}).status_code == 409
    assert client.delete(base + "/curriculum-subjects/" + component["id"], headers=headers).status_code == 409
    assert client.post(base + "/curriculum-subjects", headers=headers, json=payload).status_code == 409
    newer = post(client, context, "curricula", {**CURRICULUM, "version": 2})
    assert client.post(base + "/curricula/" + newer["id"] + "/publish", headers=headers).status_code == 422
    with Session(engine) as db, db.begin():
        tenant_context(db, curriculum["institution_id"])
        assert db.scalar(select(m.CurriculumSubject.workload_hours).where(m.CurriculumSubject.id == component["id"])) == 120
        assert len(db.scalars(select(m.AuditEvent).where(m.AuditEvent.action == "curricula.publish")).all()) == 1


def test_draft_component_update_delete_and_validation(client, context):
    headers, base = context
    curriculum, component = curriculum_with_subject(client, context)
    payload = {key: component[key] for key in ["curriculum_id", "subject_id", "workload_hours"]}
    path = base + "/curriculum-subjects/" + component["id"]
    assert client.post(base + "/curriculum-subjects", headers=headers, json=payload).status_code == 409
    assert client.put(path, headers=headers, json={**payload, "workload_hours": 0}).status_code == 422
    assert client.put(path, headers=headers, json={**payload, "workload_hours": 150}).json()["workload_hours"] == 150
    assert client.delete(path, headers=headers).status_code == 204
    assert client.post(base + "/curricula/" + curriculum["id"] + "/publish", headers=headers).status_code == 422


def test_class_calendar_curriculum_and_assignment_compatibility(client, context):
    headers, base = context
    group = {"name": "7º A", "academic_year": 2027, "grade_level": "7º ano", "shift": "morning", "capacity": 20}
    assert client.post(base + "/classes", headers=headers, json=group).status_code == 422
    post(client, context, "academic-years", YEAR)
    curriculum, component = curriculum_with_subject(client, context)
    assert client.post(base + "/classes", headers=headers, json={**group, "curriculum_id": curriculum["id"]}).status_code == 422
    client.post(base + "/curricula/" + curriculum["id"] + "/publish", headers=headers)
    assert client.post(base + "/classes", headers=headers, json={**group, "curriculum_id": curriculum["id"], "grade_level": "8º ano"}).status_code == 422
    created = post(client, context, "classes", {**group, "curriculum_id": curriculum["id"]})
    assert client.put(base + "/classes/" + created["id"], headers=headers, json=group).status_code == 409
    teacher = client.get(base + "/teachers", headers=headers).json()[0]
    subject = next(x for x in client.get(base + "/subjects", headers=headers).json() if x["id"] != component["subject_id"])
    assignment = {"class_id": created["id"], "subject_id": subject["id"], "teacher_id": teacher["id"]}
    assert client.post(base + "/assignments", headers=headers, json=assignment).status_code == 422
    assert client.post(base + "/assignments", headers=headers, json={**assignment, "subject_id": component["subject_id"]}).status_code == 201


@pytest.mark.parametrize("resource,payload", [("academic-years", YEAR), ("academic-terms", {"name": "Período", "academic_year_id": "00000000-0000-0000-0000-000000000000", "sequence": 1, "start_date": "2027-02-01", "end_date": "2027-04-01"}), ("curricula", CURRICULUM), ("curriculum-subjects", {"curriculum_id": "00000000-0000-0000-0000-000000000000", "subject_id": "00000000-0000-0000-0000-000000000000", "workload_hours": 100})])
def test_academic_permissions_and_tenant_isolation(client, context, resource, payload):
    headers, base = context
    for role in ["secretary", "teacher", "student", "guardian"]:
        auth = authenticate(client, role + "@aurora.example.com")
        assert client.post(base + "/" + resource, headers=auth, json=payload).status_code == 403
        assert client.get(base + "/" + resource, headers=auth).status_code == (200 if role == "secretary" else 403)
    other = authenticate(client, "director@horizonte.example.com")
    assert client.get(base + "/" + resource, headers=other).status_code == 404
    assert client.post(base + "/" + resource, headers=other, json=payload).status_code == 404
    coordinator = authenticate(client, "coordinator@aurora.example.com")
    assert client.get(base + "/" + resource, headers=coordinator).status_code == 200


def test_foreign_academic_ids_rejected(client, context):
    headers, base = context
    year = post(client, context, "academic-years", YEAR)
    curriculum, component = curriculum_with_subject(client, context)
    other = authenticate(client, "director@horizonte.example.com")
    other_id = client.get("/api/v1/me", headers=other).json()["memberships"][0]["institution_id"]
    other_base = "/api/v1/institutions/" + other_id
    assert client.post(other_base + "/academic-terms", headers=other, json={"name": "Intruso", "academic_year_id": year["id"], "sequence": 1, "start_date": "2027-02-01", "end_date": "2027-04-01"}).status_code == 404
    assert client.post(other_base + "/curriculum-subjects", headers=other, json={"curriculum_id": curriculum["id"], "subject_id": component["subject_id"], "workload_hours": 100}).status_code == 404
    assert client.post(other_base + "/curricula/" + curriculum["id"] + "/publish", headers=other).status_code == 404


def test_new_tables_rls_and_database_guards(client, context):
    headers, base = context
    year = post(client, context, "academic-years", YEAR)
    curriculum, component = curriculum_with_subject(client, context)
    term = post(client, context, "academic-terms", {"name": "1º bimestre", "academic_year_id": year["id"], "sequence": 1, "start_date": "2027-02-01", "end_date": "2027-04-01"})
    client.post(base + "/curricula/" + curriculum["id"] + "/publish", headers=headers)
    with Session(engine) as db, db.begin():
        for table in ["academic_years", "academic_terms", "curricula", "curriculum_subjects"]:
            assert db.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0
    for query, item in [("UPDATE curricula SET name='Changed' WHERE id=:id", curriculum),
                        ("UPDATE curriculum_subjects SET workload_hours=250 WHERE id=:id", component),
                        ("DELETE FROM curriculum_subjects WHERE id=:id", component),
                        ("UPDATE academic_terms SET end_date='2028-01-01' WHERE id=:id", term),
                        ("UPDATE academic_years SET end_date='2027-03-01' WHERE id=:id", year)]:
        with Session(engine) as db, db.begin():
            tenant_context(db, year["institution_id"])
            with pytest.raises(DBAPIError):
                db.execute(text(query), {"id": item["id"]})

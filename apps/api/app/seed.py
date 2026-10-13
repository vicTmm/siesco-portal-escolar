"""Idempotent, synthetic demo data. Run only explicitly in a local database."""
import os
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .db import engine, tenant_context
from .security import password_hasher


def seed():
    if os.environ.get("ALLOW_DEMO_SEED") != "true":
        raise RuntimeError("Defina ALLOW_DEMO_SEED=true apenas para demonstração local.")
    password = os.environ.get("DEMO_PASSWORD")
    if not password or len(password) < 12:
        raise RuntimeError("Defina DEMO_PASSWORD com pelo menos 12 caracteres.")
    with Session(engine) as db, db.begin():
        if db.scalar(select(m.User).where(m.User.email == "admin@demo.example.com")):
            print("Demonstração já cadastrada; nenhum dado alterado.")
            return
        hashed = password_hasher.hash(password)
        db.add(m.User(name="Admin Demonstração", email="admin@demo.example.com", password_hash=hashed, platform_admin=True))
        for slug, name in [("aurora", "Colégio Aurora · Demo"), ("horizonte", "Escola Horizonte · Demo")]:
            institution = m.Institution(name=name, slug=slug)
            db.add(institution)
            db.flush()
            tenant_context(db, institution.id)
            school = m.School(institution_id=institution.id, name="Unidade principal")
            db.add(school)
            db.flush()
            scope = {"institution_id": institution.id, "school_id": school.id}
            students = [m.Student(name=n + " (fictício)", birth_date=date(2014, 3, 12), **scope) for n in ["Ana Lima", "Bruno Reis", "Clara Souza", "Davi Costa"]]
            guardian = m.Guardian(name="Marina Lima (fictícia)", email=f"familia@{slug}.example.com", phone="", **scope)
            teacher = m.Teacher(name="Lucas Martins (fictício)", email=f"docente@{slug}.example.com", **scope)
            subjects = [m.Subject(name=n, code=c, **scope) for n, c in [("Matemática", "MAT"), ("Língua Portuguesa", "POR"), ("Ciências", "CIE")]]
            groups = [m.ClassGroup(name=n, academic_year=2026, grade_level="6º ano", shift="morning", capacity=30, **scope) for n in ["6º ano A", "6º ano B"]]
            db.add_all([*students, guardian, teacher, *subjects, *groups])
            db.flush()
            db.add(m.GuardianLink(student_id=students[0].id, guardian_id=guardian.id, relationship="Responsável legal", verified=True, **scope))
            for i, student in enumerate(students):
                db.add(m.Enrollment(student_id=student.id, class_id=groups[i % 2].id, academic_year=2026, **scope))
            db.add(m.Assignment(class_id=groups[0].id, subject_id=subjects[0].id, teacher_id=teacher.id, **scope))
            for role, label in [("director", "Direção"), ("coordinator", "Coordenação"), ("secretary", "Secretaria"), ("teacher", "Professor"), ("student", "Aluno"), ("guardian", "Responsável")]:
                user = m.User(name=label + " · " + slug, email=f"{role}@{slug}.example.com", password_hash=hashed)
                db.add(user)
                db.flush()
                links = {"teacher_id": teacher.id} if role == "teacher" else {"student_id": students[0].id} if role == "student" else {"guardian_id": guardian.id} if role == "guardian" else {}
                db.add(m.Membership(user_id=user.id, role=role, **scope, **links))
            db.flush()
    print("Duas instituições e contas fictícias criadas.")


if __name__ == "__main__":
    seed()

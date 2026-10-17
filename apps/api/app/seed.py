"""Idempotent, synthetic demo data. Run only explicitly in a local database."""
import os
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m
from .db import engine, tenant_context
from .security import password_hasher


def seed(*, reset_passwords=False):
    if os.environ.get("ALLOW_DEMO_SEED") != "true":
        raise RuntimeError("Defina ALLOW_DEMO_SEED=true apenas para demonstração local.")
    password = os.environ.get("DEMO_PASSWORD")
    if not password or not 6 <= len(password) <= 128:
        raise RuntimeError("Defina DEMO_PASSWORD com 6 a 128 caracteres (somente demonstração local).")
    with Session(engine) as db, db.begin():
        if reset_passwords:
            emails = ["admin@demo.example.com", *[
                f"{role}@{slug}.example.com"
                for slug in ("aurora", "horizonte")
                for role in ("director", "coordinator", "secretary", "teacher", "student", "guardian", "psychologist")
            ]]
            users = db.scalars(select(m.User).where(m.User.email.in_(emails))).all()
            for user in users:
                user.password_hash = password_hasher.hash(password)
            print(f"Senha atualizada em {len(users)} contas fictícias existentes.")
            return
        if db.scalar(select(m.User).where(m.User.email == "admin@demo.example.com")):
            # Add the newly introduced demo role without resetting existing passwords/data.
            for slug in ("aurora", "horizonte"):
                institution = db.scalar(select(m.Institution).where(m.Institution.slug == slug))
                if not institution: continue
                tenant_context(db, institution.id)
                school = db.scalar(select(m.School).where(m.School.institution_id == institution.id, m.School.name == "Unidade principal"))
                if not school: continue
                email = f"psychologist@{slug}.example.com"
                user = db.scalar(select(m.User).where(m.User.email == email))
                if not user:
                    user = m.User(name="Psicólogo escolar · " + slug, email=email, password_hash=password_hasher.hash(password))
                    db.add(user); db.flush()
                    # Existing users may have had access intentionally revoked; never regrant it.
                    db.add(m.Membership(user_id=user.id, institution_id=institution.id, school_id=school.id, role="psychologist"))
            print("Demonstração preservada; novas contas de psicologia adicionadas quando necessário.")
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
            db.add(m.AcademicYear(name="2026 · demonstração", year=2026, start_date=date(2026, 2, 2), end_date=date(2026, 12, 18), **scope))
            db.flush()
            students = [m.Student(name=n + " (fictício)", birth_date=date(2014, 3, 12), **scope) for n in ["Ana Lima", "Bruno Reis", "Clara Souza", "Davi Costa"]]
            guardian = m.Guardian(name="Marina Lima (fictícia)", email=f"familia@{slug}.example.com", phone="", **scope)
            teacher = m.Teacher(name="Lucas Martins (fictício)", email=f"docente@{slug}.example.com", **scope)
            subjects = [m.Subject(name=n, code=c, **scope) for n, c in [("Matemática", "MAT"), ("Língua Portuguesa", "POR"), ("Ciências", "CIE")]]
            groups = [m.ClassGroup(name=n, academic_year=2026, grade_level="6º ano", shift="morning", capacity=30, **scope) for n in ["6º ano A", "6º ano B"]]
            db.add_all([*students, guardian, teacher, *subjects, *groups])
            db.flush()
            db.add(m.GuardianLink(student_id=students[0].id, guardian_id=guardian.id, relationship="Responsável legal", verified=True, **scope))
            for i, student in enumerate(students):
                enrollment = m.Enrollment(student_id=student.id, class_id=groups[i % 2].id, academic_year=2026, **scope)
                db.add(enrollment)
                db.flush()
                db.add(m.Placement(enrollment_id=enrollment.id, class_id=enrollment.class_id, start_date=date(2026, 2, 2), **scope))
            db.add(m.Assignment(class_id=groups[0].id, subject_id=subjects[0].id, teacher_id=teacher.id, **scope))
            for role, label in [("director", "Direção"), ("coordinator", "Coordenação"), ("secretary", "Secretaria"), ("teacher", "Professor"), ("student", "Aluno"), ("guardian", "Responsável"), ("psychologist", "Psicólogo escolar")]:
                user = m.User(name=label + " · " + slug, email=f"{role}@{slug}.example.com", password_hash=hashed)
                db.add(user)
                db.flush()
                links = {"teacher_id": teacher.id} if role == "teacher" else {"student_id": students[0].id} if role == "student" else {"guardian_id": guardian.id} if role == "guardian" else {}
                db.add(m.Membership(user_id=user.id, role=role, **scope, **links))
            db.flush()
    print("Duas instituições e contas fictícias criadas.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-passwords", action="store_true", help="Atualiza somente as senhas das contas fictícias existentes.")
    seed(reset_passwords=parser.parse_args().reset_passwords)

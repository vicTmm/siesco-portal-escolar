from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def uid():
    return str(uuid4())


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)


class Institution(Identity, Base):
    __tablename__ = "institutions"
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True)


class School(Identity, Base):
    __tablename__ = "schools"
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    __table_args__ = (UniqueConstraint("institution_id", "id"),)


class User(Identity, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginSession(Identity, Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Identity, Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Scoped(Identity):
    institution_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    school_id: Mapped[str] = mapped_column(String(36), nullable=False)


def scope_constraints():
    return (UniqueConstraint("institution_id", "school_id", "id"),
            ForeignKeyConstraint(["institution_id", "school_id"], ["schools.institution_id", "schools.id"]))


def scoped_fk(column, table):
    return ForeignKeyConstraint(["institution_id", "school_id", column],
                                [f"{table}.institution_id", f"{table}.school_id", f"{table}.id"])


class Student(Scoped, Base):
    __tablename__ = "students"
    name: Mapped[str] = mapped_column(String(160))
    birth_date: Mapped[datetime] = mapped_column(Date)
    __table_args__ = scope_constraints()


class Guardian(Scoped, Base):
    __tablename__ = "guardians"
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(30), default="")
    __table_args__ = (*scope_constraints(), UniqueConstraint("institution_id", "school_id", "email"))


class Teacher(Scoped, Base):
    __tablename__ = "teachers"
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254))
    __table_args__ = (*scope_constraints(), UniqueConstraint("institution_id", "school_id", "email"))


class Membership(Identity, Base):
    __tablename__ = "memberships"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"))
    school_id: Mapped[str] = mapped_column(String(36))
    role: Mapped[str] = mapped_column(String(30))
    student_id: Mapped[str | None] = mapped_column(String(36))
    guardian_id: Mapped[str | None] = mapped_column(String(36))
    teacher_id: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = (UniqueConstraint("user_id", "institution_id"),
                     ForeignKeyConstraint(["institution_id", "school_id"], ["schools.institution_id", "schools.id"]),
                     scoped_fk("student_id", "students"), scoped_fk("guardian_id", "guardians"), scoped_fk("teacher_id", "teachers"),
                     CheckConstraint("role IN ('director','coordinator','secretary','teacher','student','guardian')"),
                     CheckConstraint("(role != 'student' OR student_id IS NOT NULL) AND (role != 'guardian' OR guardian_id IS NOT NULL) AND (role != 'teacher' OR teacher_id IS NOT NULL)"))


class GuardianLink(Scoped, Base):
    __tablename__ = "guardian_links"
    student_id: Mapped[str] = mapped_column(String(36))
    guardian_id: Mapped[str] = mapped_column(String(36))
    relationship: Mapped[str] = mapped_column(String(60))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (*scope_constraints(), scoped_fk("student_id", "students"), scoped_fk("guardian_id", "guardians"),
                     UniqueConstraint("institution_id", "school_id", "student_id", "guardian_id"))


class Subject(Scoped, Base):
    __tablename__ = "subjects"
    name: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(30))
    __table_args__ = (*scope_constraints(), UniqueConstraint("institution_id", "school_id", "code"))


class ClassGroup(Scoped, Base):
    __tablename__ = "classes"
    name: Mapped[str] = mapped_column(String(160))
    academic_year: Mapped[int] = mapped_column(Integer)
    grade_level: Mapped[str] = mapped_column(String(60))
    shift: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer)
    __table_args__ = (*scope_constraints(), UniqueConstraint("institution_id", "school_id", "name", "academic_year"),
                     UniqueConstraint("institution_id", "school_id", "id", "academic_year"),
                     CheckConstraint("capacity BETWEEN 1 AND 100"), CheckConstraint("academic_year BETWEEN 2000 AND 2100"),
                     CheckConstraint("shift IN ('morning','afternoon','evening','full')"))


class Assignment(Scoped, Base):
    __tablename__ = "assignments"
    class_id: Mapped[str] = mapped_column(String(36))
    subject_id: Mapped[str] = mapped_column(String(36))
    teacher_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (*scope_constraints(), scoped_fk("class_id", "classes"), scoped_fk("subject_id", "subjects"),
                     scoped_fk("teacher_id", "teachers"), UniqueConstraint("institution_id", "school_id", "class_id", "subject_id"))


class Enrollment(Scoped, Base):
    __tablename__ = "enrollments"
    student_id: Mapped[str] = mapped_column(String(36))
    class_id: Mapped[str] = mapped_column(String(36))
    academic_year: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active")
    __table_args__ = (*scope_constraints(), scoped_fk("student_id", "students"),
                     ForeignKeyConstraint(["institution_id", "school_id", "class_id", "academic_year"],
                                          ["classes.institution_id", "classes.school_id", "classes.id", "classes.academic_year"]),
                     UniqueConstraint("institution_id", "school_id", "student_id", "academic_year"),
                     CheckConstraint("status IN ('active', 'cancelled')"))


class AuditEvent(Scoped, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = scope_constraints()


TENANT_TABLES = ["schools", "students", "guardians", "teachers", "guardian_links", "subjects", "classes", "assignments", "enrollments", "audit_events"]

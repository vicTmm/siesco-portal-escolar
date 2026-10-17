from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, JSON, LargeBinary
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
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"))
    name: Mapped[str] = mapped_column(String(160))
    __table_args__ = (UniqueConstraint("institution_id", "id"),)


class User(Identity, Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(255))
    mfa_pending: Mapped[str | None] = mapped_column(String(255))
    mfa_step: Mapped[int] = mapped_column(Integer, default=0)
    mfa_recovery: Mapped[list] = mapped_column(JSON, default=list)


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
    __table_args__ = (UniqueConstraint("user_id", "institution_id", "school_id", "role"),
                     ForeignKeyConstraint(["institution_id", "school_id"], ["schools.institution_id", "schools.id"]),
                     scoped_fk("student_id", "students"), scoped_fk("guardian_id", "guardians"), scoped_fk("teacher_id", "teachers"),
                     CheckConstraint("role IN ('director','coordinator','secretary','teacher','student','guardian','psychologist')"),
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


class AcademicYear(Scoped, Base):
    __tablename__ = "academic_years"
    name: Mapped[str] = mapped_column(String(160))
    year: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (*scope_constraints(), UniqueConstraint("institution_id", "school_id", "year"),
                     CheckConstraint("year BETWEEN 2000 AND 2100"), CheckConstraint("start_date <= end_date"))


class AcademicTerm(Scoped, Base):
    __tablename__ = "academic_terms"
    name: Mapped[str] = mapped_column(String(160))
    academic_year_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date)
    __table_args__ = (*scope_constraints(), scoped_fk("academic_year_id", "academic_years"),
                     UniqueConstraint("institution_id", "school_id", "academic_year_id", "sequence"),
                     UniqueConstraint("institution_id", "school_id", "academic_year_id", "name"),
                     CheckConstraint("sequence BETWEEN 1 AND 24"), CheckConstraint("start_date <= end_date"))


class Curriculum(Scoped, Base):
    __tablename__ = "curricula"
    name: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(30))
    grade_level: Mapped[str] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    __table_args__ = (*scope_constraints(), UniqueConstraint("institution_id", "school_id", "code", "version"),
                     CheckConstraint("version BETWEEN 1 AND 999"), CheckConstraint("status IN ('draft', 'published')"))


class CurriculumSubject(Scoped, Base):
    __tablename__ = "curriculum_subjects"
    curriculum_id: Mapped[str] = mapped_column(String(36))
    subject_id: Mapped[str] = mapped_column(String(36))
    workload_hours: Mapped[int] = mapped_column(Integer)
    __table_args__ = (*scope_constraints(), scoped_fk("curriculum_id", "curricula"), scoped_fk("subject_id", "subjects"),
                     UniqueConstraint("institution_id", "school_id", "curriculum_id", "subject_id"),
                     CheckConstraint("workload_hours BETWEEN 1 AND 3000"))


class ClassGroup(Scoped, Base):
    __tablename__ = "classes"
    name: Mapped[str] = mapped_column(String(160))
    academic_year: Mapped[int] = mapped_column(Integer)
    grade_level: Mapped[str] = mapped_column(String(60))
    shift: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer)
    curriculum_id: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = (*scope_constraints(), UniqueConstraint("institution_id", "school_id", "name", "academic_year"),
                     ForeignKeyConstraint(["institution_id", "school_id", "academic_year"],
                                          ["academic_years.institution_id", "academic_years.school_id", "academic_years.year"], name="fk_classes_academic_year"),
                     scoped_fk("curriculum_id", "curricula"),
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


TENANT_TABLES = ["schools", "students", "guardians", "teachers", "guardian_links", "subjects", "academic_years", "academic_terms", "curricula", "curriculum_subjects", "classes", "assignments", "enrollments", "audit_events"]

# Learning records use one locked journal per subject/class/term.
from decimal import Decimal
from sqlalchemy import Numeric, JSON


class GradingPolicy(Scoped, Base):
    __tablename__ = "grading_policies"
    name: Mapped[str] = mapped_column(String(160))
    method: Mapped[str] = mapped_column(String(20))
    scale: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    passing: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    attendance_min: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    decimals: Mapped[int] = mapped_column(Integer)
    recovery: Mapped[str] = mapped_column(String(20))
    concepts: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (*scope_constraints(), CheckConstraint("method IN ('simple','weighted','points','concepts')"),
                     CheckConstraint("scale > 0 AND passing >= 0 AND passing <= scale"),
                     CheckConstraint("attendance_min BETWEEN 0 AND 100 AND decimals BETWEEN 0 AND 2"),
                     CheckConstraint("recovery IN ('none','best','replace','average')"))


class Journal(Scoped, Base):
    __tablename__ = "journals"
    assignment_id: Mapped[str] = mapped_column(String(36))
    term_id: Mapped[str] = mapped_column(String(36))
    policy_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (*scope_constraints(), scoped_fk("assignment_id", "assignments"), scoped_fk("term_id", "academic_terms"),
                     scoped_fk("policy_id", "grading_policies"), UniqueConstraint("institution_id", "school_id", "assignment_id", "term_id"),
                     CheckConstraint("status IN ('draft','closed','published')"), CheckConstraint("version > 0"))


class Lesson(Scoped, Base):
    __tablename__ = "lessons"
    journal_id: Mapped[str] = mapped_column(String(36))
    date: Mapped[datetime] = mapped_column(Date)
    slot: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(String(2000))
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (*scope_constraints(), scoped_fk("journal_id", "journals"),
                     UniqueConstraint("institution_id", "school_id", "journal_id", "date", "slot"), CheckConstraint("slot BETWEEN 1 AND 12"))


class Attendance(Scoped, Base):
    __tablename__ = "attendance"
    lesson_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(20))
    __table_args__ = (*scope_constraints(), scoped_fk("lesson_id", "lessons"), scoped_fk("student_id", "students"),
                     UniqueConstraint("institution_id", "school_id", "lesson_id", "student_id"), CheckConstraint("status IN ('present','absent','excused')"))


class Assessment(Scoped, Base):
    __tablename__ = "assessments"
    journal_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    date: Mapped[datetime] = mapped_column(Date)
    maximum: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    kind: Mapped[str] = mapped_column(String(20), default="regular")
    __table_args__ = (*scope_constraints(), scoped_fk("journal_id", "journals"), CheckConstraint("maximum > 0 AND weight > 0"),
                     CheckConstraint("kind IN ('regular','recovery')"))


class Grade(Scoped, Base):
    __tablename__ = "grades"
    assessment_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    value: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    __table_args__ = (*scope_constraints(), scoped_fk("assessment_id", "assessments"), scoped_fk("student_id", "students"),
                     UniqueConstraint("institution_id", "school_id", "assessment_id", "student_id"), CheckConstraint("value IS NULL OR value >= 0"))


class Publication(Scoped, Base):
    __tablename__ = "publications"
    journal_id: Mapped[str] = mapped_column(String(36))
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(), scoped_fk("journal_id", "journals"),
                     UniqueConstraint("institution_id", "school_id", "journal_id", "revision"))


class Placement(Scoped, Base):
    __tablename__ = "placements"
    enrollment_id: Mapped[str] = mapped_column(String(36))
    class_id: Mapped[str] = mapped_column(String(36))
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime | None] = mapped_column(Date)  # Exclusive.
    __table_args__ = (*scope_constraints(), scoped_fk("enrollment_id", "enrollments"), scoped_fk("class_id", "classes"),
                     CheckConstraint("end_date IS NULL OR end_date > start_date"))


class EnrollmentMovement(Scoped, Base):
    __tablename__ = "enrollment_movements"
    enrollment_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(1000))
    date: Mapped[datetime] = mapped_column(Date)
    class_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (*scope_constraints(), scoped_fk("enrollment_id", "enrollments"), scoped_fk("class_id", "classes"))


class PasswordReset(Identity, Base):
    __tablename__ = "password_resets"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


TENANT_TABLES += ["grading_policies", "journals", "lessons", "attendance", "assessments", "grades", "publications", "placements", "enrollment_movements"]


class JournalReopening(Scoped, Base):
    __tablename__ = "journal_reopenings"
    journal_id: Mapped[str] = mapped_column(String(36))
    reason: Mapped[str] = mapped_column(String(1000))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(), scoped_fk("journal_id", "journals"))


TENANT_TABLES += ['journal_reopenings']


class AnnualPolicy(Scoped, Base):
    __tablename__ = 'annual_policies'
    academic_year_id: Mapped[str] = mapped_column(String(36))
    policy_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(160))
    weights: Mapped[list] = mapped_column(JSON)
    __table_args__ = (*scope_constraints(), scoped_fk('academic_year_id','academic_years'),scoped_fk('policy_id','grading_policies'),
                     UniqueConstraint('institution_id','school_id','academic_year_id'))


class AnnualPublication(Scoped, Base):
    __tablename__ = 'annual_publications'
    annual_policy_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(),scoped_fk('annual_policy_id','annual_policies'),scoped_fk('student_id','students'),
                     UniqueConstraint('institution_id','school_id','annual_policy_id','student_id','revision'))


TENANT_TABLES += ['annual_policies','annual_publications']


class Notice(Scoped, Base):
    __tablename__ = 'notices'
    purpose: Mapped[str] = mapped_column(String(30), default='general')
    body_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[str] = mapped_column(String(1000))
    body: Mapped[str] = mapped_column(String(40000))
    kind: Mapped[str] = mapped_column(String(20))
    options: Mapped[list] = mapped_column(JSON, default=list)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (*scope_constraints(), CheckConstraint("kind IN ('notice','authorization','poll')"),CheckConstraint("purpose IN ('general','image','medication','pickup') AND (kind='authorization' OR purpose='general')",name="ck_notice_purpose"))


class NoticeRecipient(Scoped, Base):
    __tablename__ = 'notice_recipients'
    notice_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (*scope_constraints(), scoped_fk('notice_id','notices'), scoped_fk('student_id','students'),
                     UniqueConstraint('institution_id','school_id','notice_id','student_id'))


class NoticeResponse(Scoped, Base):
    __tablename__ = 'notice_responses'
    viewer_role: Mapped[str] = mapped_column(String(30), default='legacy')
    notice_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    answer: Mapped[str | None] = mapped_column(String(200))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (*scope_constraints(), ForeignKeyConstraint(["institution_id","school_id","notice_id","student_id"],["notice_recipients.institution_id","notice_recipients.school_id","notice_recipients.notice_id","notice_recipients.student_id"],name="notice_responses_audience_fk"), scoped_fk('notice_id','notices'), scoped_fk('student_id','students'),
                     UniqueConstraint('institution_id','school_id','notice_id','student_id','user_id'))


class SchoolDocument(Scoped, Base):
    __tablename__ = 'school_documents'
    student_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    token: Mapped[str] = mapped_column(String(64))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(String(1000))
    __table_args__ = (*scope_constraints(), UniqueConstraint('institution_id','id'), scoped_fk('student_id','students'), CheckConstraint("kind IN ('enrollment','attendance','report','history','contract')"))


class DocumentLookup(Identity, Base):
    __tablename__ = 'document_lookups'
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'))
    document_id: Mapped[str] = mapped_column(String(36))
    __table_args__ = (ForeignKeyConstraint(['institution_id','document_id'],['school_documents.institution_id','school_documents.id']),)


class ServiceRecord(Scoped, Base):
    __tablename__ = 'service_records'
    module: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(160))
    student_id: Mapped[str | None] = mapped_column(String(36))
    class_id: Mapped[str | None] = mapped_column(String(36))
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default='active')
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(), scoped_fk('student_id','students'), scoped_fk('class_id','classes'), CheckConstraint('version>0'))


class ServiceEvent(Scoped, Base):
    __tablename__ = 'service_events'
    record_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(), scoped_fk('record_id','service_records'))


class SensitiveGrant(Scoped, Base):
    __tablename__ = 'sensitive_grants'
    student_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    category: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (*scope_constraints(), scoped_fk('student_id','students'),
                     UniqueConstraint('institution_id','school_id','student_id','user_id','category'), CheckConstraint("category IN ('pei','health')"))


class MeetingSlot(Scoped, Base):
    __tablename__ = 'meeting_slots'
    teacher_id: Mapped[str] = mapped_column(String(36))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    student_id: Mapped[str | None] = mapped_column(String(36))
    booked_by: Mapped[str | None] = mapped_column(ForeignKey('users.id'))
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (*scope_constraints(), scoped_fk('teacher_id','teachers'), scoped_fk('student_id','students'),
                     CheckConstraint('ends_at > starts_at'), CheckConstraint('version>0'))


TENANT_TABLES += ['notices','notice_recipients','notice_responses','school_documents','service_records','service_events','sensitive_grants','meeting_slots']


class NoticeDecision(Scoped, Base):
    __tablename__ = 'notice_decisions'
    notice_id: Mapped[str] = mapped_column(String(36))
    student_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    answer: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(), ForeignKeyConstraint(["institution_id","school_id","notice_id","student_id"],["notice_recipients.institution_id","notice_recipients.school_id","notice_recipients.notice_id","notice_recipients.student_id"],name="notice_decisions_audience_fk"), scoped_fk('notice_id','notices'), scoped_fk('student_id','students'))


TENANT_TABLES += ['notice_decisions']


class PrivateAttachment(Scoped, Base):
    __tablename__ = 'private_attachments'
    record_id: Mapped[str] = mapped_column(String(36))
    filename: Mapped[str] = mapped_column(String(120))
    mime_type: Mapped[str] = mapped_column(String(40))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    uploader_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(), scoped_fk('record_id','service_records'))


TENANT_TABLES += ['private_attachments']


from sqlalchemy import Index
for _name, _table, _columns in [
    ('ix_notices_scope_date','notices',['institution_id','school_id','published_at']),
    ('ix_documents_scope_student','school_documents',['institution_id','school_id','student_id','issued_at']),
    ('ix_services_scope_module','service_records',['institution_id','school_id','module','created_at']),
    ('ix_events_scope_record','service_events',['institution_id','school_id','record_id','created_at']),
    ('ix_attachments_scope_record','private_attachments',['institution_id','school_id','record_id']),
    ('ix_meetings_scope_teacher','meeting_slots',['institution_id','school_id','teacher_id','starts_at']),
]:
    Index(_name, *(Base.metadata.tables[_table].c[column] for column in _columns))


class OfflineReceipt(Scoped, Base):
    __tablename__ = 'offline_receipts'
    journal_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    key: Mapped[str] = mapped_column(String(36))
    payload_hash: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer)
    __table_args__ = (*scope_constraints(),scoped_fk('journal_id','journals'),UniqueConstraint('institution_id','school_id','user_id','key'),CheckConstraint('version>0'))


TENANT_TABLES += ['offline_receipts']


class InventoryItem(Scoped, Base):
    __tablename__='inventory_items'
    channel: Mapped[str]=mapped_column(String(20))
    code: Mapped[str]=mapped_column(String(60))
    name: Mapped[str]=mapped_column(String(160))
    price_cents: Mapped[int]=mapped_column(Integer)
    stock: Mapped[int]=mapped_column(Integer)
    tags: Mapped[list]=mapped_column(JSON,default=list)
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    version: Mapped[int]=mapped_column(Integer,default=1)
    __table_args__=(*scope_constraints(),UniqueConstraint('institution_id','school_id','channel','code'),CheckConstraint("channel IN ('canteen','store')"),CheckConstraint('price_cents>0 AND price_cents<=10000000 AND stock>=0 AND stock<=1000000 AND version>0'))


class WalletPolicy(Scoped, Base):
    __tablename__='wallet_policies'
    student_id: Mapped[str]=mapped_column(String(36))
    encrypted: Mapped[bytes]=mapped_column(LargeBinary)
    version: Mapped[int]=mapped_column(Integer,default=1)
    __table_args__=(*scope_constraints(),scoped_fk('student_id','students'),UniqueConstraint('institution_id','school_id','student_id'),CheckConstraint('version>0'))


class WalletEntry(Scoped, Base):
    __tablename__='wallet_entries'
    student_id: Mapped[str]=mapped_column(String(36))
    actor_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    key: Mapped[str]=mapped_column(String(36))
    payload_hash: Mapped[str]=mapped_column(String(64))
    kind: Mapped[str]=mapped_column(String(20))
    channel: Mapped[str | None]=mapped_column(String(20))
    amount_cents: Mapped[int]=mapped_column(Integer)
    note: Mapped[str]=mapped_column(String(1000))
    lines: Mapped[list]=mapped_column(JSON,default=list)
    reverses_id: Mapped[str | None]=mapped_column(String(36))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    __table_args__=(*scope_constraints(),scoped_fk('student_id','students'),scoped_fk('reverses_id','wallet_entries'),UniqueConstraint('institution_id','school_id','key'),UniqueConstraint('institution_id','school_id','reverses_id'),CheckConstraint("kind IN ('credit','debit','refund')"),CheckConstraint('amount_cents>0 AND amount_cents<=1000000000'))


class StoreOrder(Scoped, Base):
    __tablename__='store_orders'
    entry_id: Mapped[str]=mapped_column(String(36))
    status: Mapped[str]=mapped_column(String(20),default='placed')
    version: Mapped[int]=mapped_column(Integer,default=1)
    __table_args__=(*scope_constraints(),scoped_fk('entry_id','wallet_entries'),UniqueConstraint('institution_id','school_id','entry_id'),CheckConstraint("status IN ('placed','delivered','cancelled')"),CheckConstraint('version>0'))


TENANT_TABLES += ['inventory_items','wallet_policies','wallet_entries','store_orders']
Index('ix_wallet_scope_student_date',WalletEntry.institution_id,WalletEntry.school_id,WalletEntry.student_id,WalletEntry.created_at)


class PickupCode(Scoped, Base):
    __tablename__='pickup_codes'
    record_id: Mapped[str]=mapped_column(String(36))
    token_hash: Mapped[str]=mapped_column(String(64),unique=True)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    __table_args__=(*scope_constraints(),scoped_fk('record_id','service_records'))


TENANT_TABLES += ['pickup_codes']


class NotificationDismissal(Scoped, Base):
    __tablename__='notification_dismissals'
    user_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    key: Mapped[str]=mapped_column(String(200))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    __table_args__=(*scope_constraints(),UniqueConstraint('institution_id','school_id','user_id','key'))


TENANT_TABLES += ['notification_dismissals']


class FiscalProfile(Scoped, Base):
    __tablename__ = 'fiscal_profiles'
    cnpj: Mapped[str] = mapped_column(String(14))
    environment: Mapped[str] = mapped_column(String(20))
    series: Mapped[int] = mapped_column(Integer)
    next_number: Mapped[int] = mapped_column(BigInteger)
    encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (*scope_constraints(), UniqueConstraint('institution_id','school_id'), CheckConstraint("environment IN ('test','production')"), CheckConstraint('series>=1 AND series<=49999 AND next_number>0 AND next_number<=999999999999999 AND version>0'))


class FiscalInvoice(Scoped, Base):
    __tablename__ = 'fiscal_invoices'
    student_id: Mapped[str] = mapped_column(String(36))
    guardian_id: Mapped[str] = mapped_column(String(36))
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    key: Mapped[str] = mapped_column(String(36))
    payload_hash: Mapped[str] = mapped_column(String(64))
    environment: Mapped[str] = mapped_column(String(20))
    cnpj: Mapped[str] = mapped_column(String(14))
    series: Mapped[int] = mapped_column(Integer)
    number: Mapped[int] = mapped_column(BigInteger)
    dps_id: Mapped[str] = mapped_column(String(45))
    encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    signed_xml: Mapped[bytes | None] = mapped_column(LargeBinary)
    authorized_xml: Mapped[bytes | None] = mapped_column(LargeBinary)
    access_key: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default='draft')
    message: Mapped[str] = mapped_column(String(1000), default='Rascunho fiscal. Não é nota autorizada.')
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (*scope_constraints(), scoped_fk('student_id','students'), scoped_fk('guardian_id','guardians'), UniqueConstraint('institution_id','school_id','key'), UniqueConstraint('cnpj','environment','series','number'), CheckConstraint("environment IN ('test','production')"), CheckConstraint("status IN ('draft','submitting','authorized','rejected','unknown')"), CheckConstraint('version>0 AND number>0'))


TENANT_TABLES += ['fiscal_profiles','fiscal_invoices']
Index('ix_fiscal_invoice_scope_date',FiscalInvoice.institution_id,FiscalInvoice.school_id,FiscalInvoice.created_at)

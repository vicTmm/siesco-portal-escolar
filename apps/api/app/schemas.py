from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class Login(Schema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    otp: str = Field(default="", max_length=64)


class PersonIn(Schema):
    name: str = Field(min_length=2, max_length=160)


class StudentIn(PersonIn):
    birth_date: date

    @field_validator("birth_date")
    @classmethod
    def valid_birth(cls, value):
        if value > date.today() or value.year < 1900:
            raise ValueError("Data de nascimento inválida")
        return value


class TeacherIn(PersonIn):
    email: EmailStr


class GuardianIn(TeacherIn):
    phone: str = Field(default="", max_length=30, pattern=r"^[\d +().-]*$")


class InstitutionIn(PersonIn):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    director_name: str = Field(min_length=2, max_length=160)
    director_email: EmailStr
    director_password: str = Field(min_length=12, max_length=128)


class SubjectIn(PersonIn):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9_-]+$")


class ClassIn(PersonIn):
    academic_year: int = Field(ge=2000, le=2100)
    grade_level: str = Field(min_length=2, max_length=60)
    shift: Literal["morning", "afternoon", "evening", "full"]
    capacity: int = Field(ge=1, le=100)
    curriculum_id: UUID | None = None


class DateRangeIn(PersonIn):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def ordered_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("A data final deve ser igual ou posterior à data inicial.")
        return self


class AcademicYearIn(DateRangeIn):
    year: int = Field(ge=2000, le=2100)


class AcademicTermIn(DateRangeIn):
    academic_year_id: UUID
    sequence: int = Field(ge=1, le=24)


class CurriculumIn(PersonIn):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9_-]+$")
    grade_level: str = Field(min_length=2, max_length=60)
    version: int = Field(ge=1, le=999)


class CurriculumSubjectIn(Schema):
    curriculum_id: UUID
    subject_id: UUID
    workload_hours: int = Field(ge=1, le=3000)


class LinkIn(Schema):
    student_id: UUID
    guardian_id: UUID
    relationship: str = Field(min_length=2, max_length=60)
    verified: bool = False


class AssignmentIn(Schema):
    class_id: UUID
    subject_id: UUID
    teacher_id: UUID


class EnrollmentIn(Schema):
    student_id: UUID
    class_id: UUID


class AccountIn(TeacherIn):
    password: str = Field(min_length=12, max_length=128)
    role: Literal["director", "coordinator", "secretary", "teacher", "student", "guardian"]
    person_id: UUID | None = None


class RecordOut(Schema):
    id: str
    institution_id: str
    school_id: str


class StudentOut(StudentIn, RecordOut):
    pass


class GuardianOut(GuardianIn, RecordOut):
    pass


class TeacherOut(TeacherIn, RecordOut):
    pass


class SubjectOut(SubjectIn, RecordOut):
    pass


class ClassOut(ClassIn, RecordOut):
    pass


class AcademicYearOut(AcademicYearIn, RecordOut):
    needs_review: bool


class AcademicTermOut(AcademicTermIn, RecordOut):
    pass


class CurriculumOut(CurriculumIn, RecordOut):
    status: Literal["draft", "published"]


class CurriculumSubjectOut(CurriculumSubjectIn, RecordOut):
    pass


class LinkOut(LinkIn, RecordOut):
    pass


class AssignmentOut(AssignmentIn, RecordOut):
    pass


class EnrollmentOut(EnrollmentIn, RecordOut):
    academic_year: int
    status: str


class InstitutionOut(Schema):
    id: str
    name: str
    slug: str


class TokenOut(Schema):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int


class MembershipOut(Schema):
    institution_id: str
    institution_name: str
    school_id: str
    role: str


class MeOut(Schema):
    id: str
    name: str
    email: str
    platform_admin: bool
    memberships: list[MembershipOut]


class AccountOut(Schema):
    id: str
    name: str
    email: str
    role: str


class OccupancyOut(Schema):
    name: str
    capacity: int
    enrolled: int


class DashboardOut(Schema):
    counts: dict[str, int]
    occupancy: list[OccupancyOut]


class PortalStudentOut(Schema):
    id: str
    name: str


class PortalOut(Schema):
    students: list[PortalStudentOut]
    message: str

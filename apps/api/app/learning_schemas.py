from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from .schemas import Schema


class Concept(Schema):
    label: str = Field(min_length=1, max_length=30)
    minimum: Decimal = Field(ge=0, le=100)


class PolicyIn(Schema):
    name: str = Field(min_length=2, max_length=160)
    method: Literal['simple', 'weighted', 'points', 'concepts']
    scale: Decimal = Field(gt=0, le=1000, decimal_places=2)
    passing: Decimal = Field(ge=0, decimal_places=2)
    attendance_min: Decimal = Field(ge=0, le=100, decimal_places=2)
    decimals: int = Field(ge=0, le=2)
    recovery: Literal['none', 'best', 'replace', 'average']
    concepts: list[Concept] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def valid(self):
        if self.passing > self.scale:
            raise ValueError('Média mínima maior que a escala.')
        if self.method == 'concepts' and (not self.concepts or min(c.minimum for c in self.concepts) != 0):
            raise ValueError('Conceitos exigem faixas, incluindo uma iniciando em zero.')
        if len({c.minimum for c in self.concepts}) != len(self.concepts) or len({c.label for c in self.concepts}) != len(self.concepts):
            raise ValueError('Faixas e nomes dos conceitos devem ser únicos.')
        return self


class JournalIn(Schema):
    assignment_id: UUID
    term_id: UUID
    policy_id: UUID


class VersionIn(Schema):
    version: int = Field(ge=1)


class ReopenIn(VersionIn):
    reason: str = Field(min_length=10, max_length=1000)


class LessonIn(VersionIn):
    date: date
    slot: int = Field(ge=1, le=12)
    content: str = Field(min_length=2, max_length=2000)


class AttendanceEntry(Schema):
    student_id: UUID
    status: Literal['present', 'absent', 'excused']


class AttendanceIn(VersionIn):
    entries: list[AttendanceEntry] = Field(min_length=1, max_length=100)


class AssessmentIn(VersionIn):
    name: str = Field(min_length=2, max_length=160)
    date: date
    maximum: Decimal = Field(gt=0, le=1000, decimal_places=2)
    weight: Decimal = Field(gt=0, le=1000, decimal_places=2)
    kind: Literal['regular', 'recovery'] = 'regular'


class GradeEntry(Schema):
    student_id: UUID
    value: Decimal | None = Field(default=None, ge=0, decimal_places=2)


class GradesIn(VersionIn):
    entries: list[GradeEntry] = Field(min_length=1, max_length=100)


class MoveIn(Schema):
    action: Literal['transfer', 'cancel', 'reactivate']
    class_id: UUID | None = None
    date: date
    reason: str = Field(min_length=10, max_length=1000)

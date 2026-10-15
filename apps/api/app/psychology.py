"""Private psychology consultations: authoring psychologist and school directors only."""

import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy.orm import Session
from . import models as m
from .db import database
from .domain import scoped, find, create, audit
from .mfa import cipher
from .schemas import Schema
from .security import membership, permit

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}/psychology",
    tags=["Psicologia escolar"],
)
ROLES = {"psychologist", "director"}


class ConsultationIn(Schema):
    student_id: UUID
    occurred_at: datetime
    kind: Literal["initial", "follow_up", "assessment", "family", "referral"]
    observations: str = Field(min_length=3, max_length=8000)
    analysis: str = Field(min_length=3, max_length=8000)
    plan: str = Field(min_length=3, max_length=4000)
    next_visit: datetime | None = None
    professional_registration: str = Field(default="", max_length=40)

    @model_validator(mode="after")
    def dates(self):
        if self.occurred_at.tzinfo is None or (
            self.next_visit and self.next_visit.tzinfo is None
        ):
            raise ValueError("Informe data e hora com fuso horário.")
        if self.occurred_at > datetime.now(timezone.utc):
            raise ValueError(
                "Registre atendimentos já realizados; use o retorno para agendar o acompanhamento."
            )
        if self.next_visit and self.next_visit <= self.occurred_at:
            raise ValueError("O retorno deve ocorrer depois do atendimento.")
        return self


class NoteIn(Schema):
    text: str = Field(min_length=3, max_length=8000)
    version: int = Field(ge=1)


def authorize(member, record, write=False):
    permit(member, ROLES)
    if record.module != "psychology" or (
        member.role == "psychologist" and record.owner_id != member.user_id
    ):
        raise HTTPException(404, "Atendimento não encontrado.")
    if write and (member.role != "psychologist" or record.owner_id != member.user_id):
        raise HTTPException(
            403,
            "Somente o psicólogo autor pode acrescentar informações ao atendimento.",
        )
    return record


def dto(db, member, record):
    data = json.loads(cipher().decrypt(record.data["encrypted"].encode()))
    student = find(db, m.Student, record.student_id, member)
    professional = db.get(m.User, record.owner_id)
    return {
        "id": record.id,
        "student_id": student.id,
        "student": student.name,
        "professional": professional.name,
        "can_write": member.role == "psychologist"
        and record.owner_id == member.user_id,
        "version": record.version,
        "created_at": record.created_at,
        "data": data,
    }


@router.get("/students")
def students(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str = Query("", max_length=100),
):
    permit(member, ROLES)
    statement = scoped(m.Student, member)
    if q:
        statement = statement.where(m.Student.name.icontains(q, autoescape=True))
    return [
        {"id": s.id, "name": s.name}
        for s in db.scalars(
            statement.order_by(m.Student.name, m.Student.id).offset(offset).limit(limit)
        )
    ]


@router.get("")
def consultations(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    student_id: UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, ROLES)
    statement = scoped(m.ServiceRecord, member).where(
        m.ServiceRecord.module == "psychology"
    )
    if member.role == "psychologist":
        statement = statement.where(m.ServiceRecord.owner_id == member.user_id)
    if student_id:
        find(db, m.Student, student_id, member)
        statement = statement.where(m.ServiceRecord.student_id == str(student_id))
    records = db.scalars(
        statement.order_by(m.ServiceRecord.created_at.desc(), m.ServiceRecord.id)
        .offset(offset)
        .limit(limit)
    ).all()
    audit(
        db,
        member,
        "psychology.read",
        str(student_id) if student_id else member.school_id,
    )
    return [dto(db, member, r) for r in records]


@router.post("", status_code=201)
def register(
    payload: ConsultationIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"psychologist"})
    find(db, m.Student, payload.student_id, member)
    content = payload.model_dump(mode="json", exclude={"student_id"})
    record = create(
        db,
        m.ServiceRecord,
        {
            "module": "psychology",
            "title": "Atendimento psicológico confidencial",
            "student_id": str(payload.student_id),
            "owner_id": member.user_id,
            "status": "recorded",
            "data": {
                "encrypted": cipher()
                .encrypt(json.dumps(content, ensure_ascii=False).encode())
                .decode()
            },
        },
        member,
    )
    return dto(db, member, record)


@router.post("/{item_id}/notes", status_code=201)
def append_note(
    item_id: UUID,
    payload: NoteIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    record = authorize(
        member, find(db, m.ServiceRecord, item_id, member, lock=True), write=True
    )
    if payload.version != record.version:
        raise HTTPException(
            409,
            "O atendimento foi atualizado. Recarregue antes de acrescentar a evolução.",
        )
    create(
        db,
        m.ServiceEvent,
        {
            "record_id": record.id,
            "actor_id": member.user_id,
            "action": "psychology_note",
            "data": {
                "encrypted": cipher()
                .encrypt(
                    json.dumps({"text": payload.text}, ensure_ascii=False).encode()
                )
                .decode()
            },
        },
        member,
    )
    record.version += 1
    return dto(db, member, record)

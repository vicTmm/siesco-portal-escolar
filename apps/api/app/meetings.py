"""Atomic bookings in teacher office-hour slots."""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .domain import scoped, find, create, audit
from .db import database
from .security import membership, permit, MANAGERS
from .community import student_ids

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Agenda de reuniões"]
)


class SlotIn(Schema):
    teacher_id: UUID
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def dates(self):
        if (
            not self.starts_at.tzinfo
            or not self.ends_at.tzinfo
            or self.starts_at <= datetime.now(timezone.utc)
            or not 300 <= (self.ends_at - self.starts_at).total_seconds() <= 14400
        ):
            raise ValueError(
                "Agende no futuro, com fuso horário e duração entre 5 minutos e 4 horas."
            )
        return self


class BookingIn(Schema):
    student_id: UUID
    version: int = Field(ge=1)


class CancelIn(Schema):
    version: int = Field(ge=1)


def dto(db, member, s):
    own = (
        member.role in MANAGERS
        or (member.role == "teacher" and s.teacher_id == member.teacher_id)
        or s.booked_by == member.user_id
    )
    return {
        "id": s.id,
        "teacher": find(db, m.Teacher, s.teacher_id, member).name,
        "starts_at": s.starts_at,
        "ends_at": s.ends_at,
        "booked": bool(s.student_id),
        "student": find(db, m.Student, s.student_id, member).name
        if s.student_id and own
        else None,
        "can_cancel": bool(s.student_id) and own,
        "version": s.version,
    }


@router.get("/meetings")
def slots(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, MANAGERS | {"teacher", "guardian"})
    stmt = scoped(m.MeetingSlot, member).where(
        m.MeetingSlot.starts_at > datetime.now(timezone.utc)
    )
    if member.role == "teacher":
        stmt = stmt.where(m.MeetingSlot.teacher_id == member.teacher_id)
    return [
        dto(db, member, s)
        for s in db.scalars(
            stmt.order_by(m.MeetingSlot.starts_at, m.MeetingSlot.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/meetings", status_code=201)
def add(
    payload: SlotIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS | {"teacher"})
    if member.role == "teacher" and str(payload.teacher_id) != member.teacher_id:
        raise HTTPException(403, "Abra horários apenas na sua agenda.")
    find(db, m.Teacher, payload.teacher_id, member, lock=True)
    if db.scalar(
        scoped(m.MeetingSlot, member).where(
            m.MeetingSlot.teacher_id == str(payload.teacher_id),
            m.MeetingSlot.starts_at < payload.ends_at,
            m.MeetingSlot.ends_at > payload.starts_at,
        )
    ):
        raise HTTPException(
            409, "Este horário sobrepõe outro compromisso do professor."
        )
    s = create(
        db,
        m.MeetingSlot,
        {**payload.model_dump(), "teacher_id": str(payload.teacher_id)},
        member,
    )
    return dto(db, member, s)


@router.post("/meetings/{item_id}/book")
def book(
    item_id: UUID,
    payload: BookingIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS | {"guardian"})
    if str(payload.student_id) not in student_ids(db, member):
        raise HTTPException(404, "Aluno não encontrado.")
    s = find(db, m.MeetingSlot, item_id, member, lock=True)
    if (
        s.student_id
        or s.version != payload.version
        or s.starts_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(
            409, "Este horário não está mais disponível. Recarregue a agenda."
        )
    s.student_id = str(payload.student_id)
    s.booked_by = member.user_id
    s.version += 1
    audit(db, member, "meetings.book", s.id)
    return dto(db, member, s)


@router.post("/meetings/{item_id}/cancel")
def cancel(
    item_id: UUID,
    payload: CancelIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    s = find(db, m.MeetingSlot, item_id, member, lock=True)
    if not (
        member.role in MANAGERS
        or (member.role == "teacher" and s.teacher_id == member.teacher_id)
        or s.booked_by == member.user_id
    ):
        raise HTTPException(403, "Sem permissão para cancelar esta reserva.")
    if s.version != payload.version:
        raise HTTPException(409, "A agenda foi atualizada. Recarregue.")
    s.student_id = None
    s.booked_by = None
    s.version += 1
    audit(db, member, "meetings.cancel", s.id)
    return dto(db, member, s)


@router.get("/meeting-teachers")
def teachers(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    permit(member, MANAGERS | {"teacher"})
    stmt = scoped(m.Teacher, member)
    if member.role == "teacher":
        stmt = stmt.where(m.Teacher.id == member.teacher_id)
    return [
        {"id": t.id, "name": t.name}
        for t in db.scalars(
            stmt.order_by(m.Teacher.name, m.Teacher.id).offset(offset).limit(limit)
        )
    ]

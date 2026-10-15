"""Atomic and idempotent synchronization of explicitly prepared offline journals."""

import hashlib
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from . import models as m, learning_schemas as s
from .schemas import Schema
from .db import database
from .domain import scoped, find, create
from .security import membership, permit
from .learning import journal_access, add_lesson, attendance

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Diário offline"]
)


class OfflineLesson(Schema):
    date: date
    slot: int = Field(ge=1, le=12)
    content: str = Field(min_length=2, max_length=2000)
    entries: list[s.AttendanceEntry] = Field(min_length=1, max_length=100)


class OfflineAttendance(Schema):
    lesson_id: UUID
    entries: list[s.AttendanceEntry] = Field(min_length=1, max_length=100)


class SyncIn(Schema):
    key: UUID
    version: int = Field(ge=1)
    lessons: list[OfflineLesson] = Field(default_factory=list, max_length=10)
    attendance: list[OfflineAttendance] = Field(default_factory=list, max_length=20)


@router.post("/journals/{item_id}/offline-sync")
def sync(
    item_id: UUID,
    payload: SyncIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director", "coordinator", "teacher"})
    journal = journal_access(db, member, item_id)
    digest = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    receipt = db.scalar(
        scoped(m.OfflineReceipt, member).where(
            m.OfflineReceipt.user_id == member.user_id,
            m.OfflineReceipt.key == str(payload.key),
        )
    )
    if receipt:
        if receipt.payload_hash != digest or receipt.journal_id != journal.id:
            raise HTTPException(
                409, "Identificador de sincronização usado por outro rascunho."
            )
        return {"version": receipt.version, "already_applied": True}
    journal_access(db, member, item_id, payload.version, True)
    if not payload.lessons and not payload.attendance:
        raise HTTPException(422, "Nenhum rascunho para sincronizar.")
    if len({a.lesson_id for a in payload.attendance}) != len(payload.attendance):
        raise HTTPException(422, "Aula duplicada no lote.")
    version = journal.version
    for lesson in payload.lessons:
        created = add_lesson(
            item_id,
            s.LessonIn(
                version=version,
                date=lesson.date,
                slot=lesson.slot,
                content=lesson.content,
            ),
            member,
            db,
        )
        version = attendance(
            UUID(created["id"]),
            s.AttendanceIn(version=created["version"], entries=lesson.entries),
            member,
            db,
        )["version"]
    for change in payload.attendance:
        lesson = find(db, m.Lesson, change.lesson_id, member)
        if lesson.journal_id != journal.id:
            raise HTTPException(422, "Aula de outro diário.")
        version = attendance(
            change.lesson_id,
            s.AttendanceIn(version=version, entries=change.entries),
            member,
            db,
        )["version"]
    create(
        db,
        m.OfflineReceipt,
        {
            "journal_id": journal.id,
            "user_id": member.user_id,
            "key": str(payload.key),
            "payload_hash": digest,
            "version": version,
        },
        member,
    )
    return {"version": version, "already_applied": False}


@router.get("/journals/{item_id}/offline-package")
def package(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    from sqlalchemy import select
    from .learning import journal_detail

    permit(member, {"director", "coordinator", "teacher"})
    j = journal_access(db, member, item_id)
    assignment = find(db, m.Assignment, j.assignment_id, member)
    term = find(db, m.AcademicTerm, j.term_id, member)
    placements = db.execute(
        select(m.Enrollment.student_id, m.Placement.start_date, m.Placement.end_date)
        .join(m.Placement, m.Placement.enrollment_id == m.Enrollment.id)
        .where(
            m.Enrollment.institution_id == member.institution_id,
            m.Enrollment.school_id == member.school_id,
            m.Placement.class_id == assignment.class_id,
        )
    ).all()
    return {
        **journal_detail(item_id, member, db),
        "term_start": term.start_date,
        "term_end": term.end_date,
        "placements": [
            {"student_id": sid, "start": start, "end": end}
            for sid, start, end in placements
        ],
    }

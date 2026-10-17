"""Institutional notices, reading receipts, polls and recorded guardian decisions."""

from datetime import datetime, timezone
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find, create, audit
from .security import membership, permit, MANAGERS
from .mfa import cipher

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Comunicação institucional"]
)


def student_ids(db, member):
    stmt = scoped(m.Student, member)
    if member.role in MANAGERS:
        return set(db.scalars(stmt.with_only_columns(m.Student.id)))
    if member.role == "student":
        return {member.student_id}
    if member.role == "guardian":
        return set(
            db.scalars(
                scoped(m.GuardianLink, member)
                .with_only_columns(m.GuardianLink.student_id)
                .where(
                    m.GuardianLink.guardian_id == member.guardian_id,
                    m.GuardianLink.verified.is_(True),
                )
            )
        )
    if member.role == "teacher":
        return set(
            db.scalars(
                scoped(m.Enrollment, member)
                .with_only_columns(m.Enrollment.student_id)
                .where(
                    m.Enrollment.status == "active",
                    m.Enrollment.class_id.in_(
                        select(m.Assignment.class_id).where(
                            m.Assignment.teacher_id == member.teacher_id
                        )
                    ),
                )
            )
        )
    return set()


class NoticeIn(Schema):
    purpose: Literal["general", "image", "medication", "pickup"] = "general"
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=3, max_length=6000)
    kind: Literal["notice", "authorization", "poll"] = "notice"
    class_id: UUID | None = None
    student_id: UUID | None = None
    shift: Literal["morning", "afternoon", "evening", "full"] | None = None
    academic_year: int = Field(ge=2000, le=2100)
    options: list[str] = Field(default_factory=list, max_length=10)
    deadline: datetime | None = None

    @model_validator(mode="after")
    def valid_options(self):
        if self.kind != "authorization" and self.purpose != "general":
            raise ValueError("A finalidade específica é usada em autorizações.")
        if self.kind == "poll" and (
            len(self.options) < 2
            or len(set(self.options)) != len(self.options)
            or any(not 1 <= len(o) <= 200 for o in self.options)
        ):
            raise ValueError("Enquetes precisam de 2 a 10 opções distintas.")
        if self.kind != "poll" and self.options:
            raise ValueError("Opções são usadas apenas em enquetes.")
        if self.deadline and (
            self.deadline.tzinfo is None or self.deadline <= datetime.now(timezone.utc)
        ):
            raise ValueError("O prazo deve ser futuro e incluir fuso horário.")
        return self


class DecisionIn(Schema):
    student_id: UUID
    answer: str | None = Field(default=None, max_length=200)


def medical_ids(db, member):
    if member.role == "director":
        return student_ids(db, member)
    if member.role == "guardian":
        return student_ids(db, member)
    if member.role == "student":
        return set()
    return set(
        db.scalars(
            scoped(m.SensitiveGrant, member)
            .with_only_columns(m.SensitiveGrant.student_id)
            .where(
                m.SensitiveGrant.user_id == member.user_id,
                m.SensitiveGrant.category == "health",
                m.SensitiveGrant.active.is_(True),
            )
        )
    )


def notice_students(db, member, notice):
    return (
        medical_ids(db, member)
        if notice.purpose == "medication"
        else student_ids(db, member)
    )


def accessible(db, member, identifier):
    notice = find(db, m.Notice, identifier, member)
    if member.role in MANAGERS and notice.purpose != "medication":
        return notice
    allowed = notice_students(db, member, notice)
    if (notice.archived and member.role not in MANAGERS) or not db.scalar(
        scoped(m.NoticeRecipient, member).where(
            m.NoticeRecipient.notice_id == notice.id,
            m.NoticeRecipient.student_id.in_(allowed),
        )
    ):
        raise HTTPException(404, "Comunicado não encontrado.")
    return notice


def serialize(db, member, notice):
    if notice.purpose == "medication":
        audit(db, member, "notices.medical_read", notice.id)
    allowed = notice_students(db, member, notice)
    recipients = db.scalars(
        scoped(m.NoticeRecipient, member).where(
            m.NoticeRecipient.notice_id == notice.id,
            m.NoticeRecipient.student_id.in_(allowed),
        )
    ).all()
    own = db.scalars(
        scoped(m.NoticeResponse, member).where(
            m.NoticeResponse.notice_id == notice.id,
            m.NoticeResponse.user_id == member.user_id,
            m.NoticeResponse.student_id.in_(allowed),
        )
    ).all()
    return {
        "id": notice.id,
        "title": cipher().decrypt(notice.title.encode()).decode()
        if notice.body_encrypted
        else notice.title,
        "body": cipher().decrypt(notice.body.encode()).decode()
        if notice.body_encrypted
        else notice.body,
        "kind": notice.kind,
        "purpose": notice.purpose,
        "options": notice.options,
        "deadline": notice.deadline,
        "published_at": notice.published_at,
        "archived": notice.archived,
        "students": [
            {"id": r.student_id, "name": find(db, m.Student, r.student_id, member).name}
            for r in recipients
        ],
        "responses": [
            {
                "student_id": r.student_id,
                "viewer_role": r.viewer_role,
                "read_at": r.read_at,
                "answer": r.answer,
                "answered_at": r.answered_at,
            }
            for r in own
        ],
    }


@router.get("/notices")
def notices(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    stmt = scoped(m.Notice, member)
    normal = select(m.NoticeRecipient.notice_id).where(
        m.NoticeRecipient.student_id.in_(student_ids(db, member))
    )
    medical = select(m.NoticeRecipient.notice_id).where(
        m.NoticeRecipient.student_id.in_(medical_ids(db, member))
    )
    if member.role in MANAGERS:
        stmt = stmt.where(
            or_(m.Notice.purpose != "medication", m.Notice.id.in_(medical))
        )
    else:
        stmt = stmt.where(
            m.Notice.archived.is_(False),
            or_(
                and_(m.Notice.purpose != "medication", m.Notice.id.in_(normal)),
                and_(m.Notice.purpose == "medication", m.Notice.id.in_(medical)),
            ),
        )
    rows = db.scalars(
        stmt.order_by(m.Notice.published_at.desc(), m.Notice.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [serialize(db, member, n) for n in rows]


@router.post("/notices", status_code=201)
def publish(
    payload: NoticeIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS)
    if payload.purpose == "medication":
        if not payload.student_id:
            raise HTTPException(
                422,
                "Autorizações de medicação devem ser destinadas a um aluno específico.",
            )
        if str(payload.student_id) not in medical_ids(db, member):
            raise HTTPException(403, "Acesso de saúde não concedido para este aluno.")
    groups = (
        scoped(m.ClassGroup, member)
        .with_only_columns(m.ClassGroup.id)
        .where(m.ClassGroup.academic_year == payload.academic_year)
    )
    if payload.class_id:
        find(db, m.ClassGroup, payload.class_id, member)
        groups = groups.where(m.ClassGroup.id == str(payload.class_id))
    if payload.shift:
        groups = groups.where(m.ClassGroup.shift == payload.shift)
    audience = (
        scoped(m.Enrollment, member)
        .with_only_columns(m.Enrollment.student_id)
        .where(m.Enrollment.status == "active", m.Enrollment.class_id.in_(groups))
    )
    if payload.student_id:
        find(db, m.Student, payload.student_id, member)
        audience = audience.where(m.Enrollment.student_id == str(payload.student_id))
    students = set(db.scalars(audience))
    if not students:
        raise HTTPException(
            422, "Nenhum aluno com matrícula ativa corresponde ao público selecionado."
        )
    n = create(
        db,
        m.Notice,
        {
            **payload.model_dump(
                exclude={"class_id", "student_id", "shift", "academic_year"}
            ),
            "author_id": member.user_id,
            "body_encrypted": payload.purpose == "medication",
            **(
                {
                    "title": cipher().encrypt(payload.title.encode()).decode(),
                    "body": cipher().encrypt(payload.body.encode()).decode(),
                }
                if payload.purpose == "medication"
                else {}
            ),
        },
        member,
    )
    db.add_all(
        [
            m.NoticeRecipient(
                notice_id=n.id,
                student_id=s,
                institution_id=member.institution_id,
                school_id=member.school_id,
            )
            for s in students
        ]
    )
    db.flush()
    return serialize(db, member, n)


@router.post("/notices/{item_id}/respond")
def respond(
    item_id: UUID,
    payload: DecisionIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    notice = accessible(db, member, item_id)
    find(db, m.Notice, item_id, member, lock=True)
    sid = str(payload.student_id)
    if sid not in notice_students(db, member, notice) or not db.scalar(
        scoped(m.NoticeRecipient, member).where(
            m.NoticeRecipient.notice_id == notice.id,
            m.NoticeRecipient.student_id == sid,
        )
    ):
        raise HTTPException(404, "Destinatário não encontrado.")
    if notice.archived:
        raise HTTPException(409, "Comunicado arquivado.")
    if payload.answer is not None:
        permit(member, {"guardian"})
        if (
            notice.deadline
            and notice.deadline < datetime.now(timezone.utc)
            and payload.answer != "withdraw"
        ):
            raise HTTPException(409, "O prazo de resposta terminou.")
        choices = (
            notice.options
            if notice.kind == "poll"
            else ["yes", "no", "withdraw"]
            if notice.kind == "authorization"
            else []
        )
        if payload.answer not in choices:
            raise HTTPException(422, "Resposta inválida para este comunicado.")
    row = db.scalar(
        scoped(m.NoticeResponse, member).where(
            m.NoticeResponse.notice_id == notice.id,
            m.NoticeResponse.student_id == sid,
            m.NoticeResponse.user_id == member.user_id,
        )
    )
    if not row:
        row = create(
            db,
            m.NoticeResponse,
            {"notice_id": notice.id, "student_id": sid, "user_id": member.user_id},
            member,
        )
    if row.viewer_role != "guardian" and (
        row.viewer_role == "legacy" or member.role == "guardian"
    ):
        row.viewer_role = member.role
        row.read_at = datetime.now(timezone.utc)
    if payload.answer is not None:
        row.answer = payload.answer
        row.answered_at = datetime.now(timezone.utc)
        # Immutable decisions preserve the exact text and decision trail, including withdrawal.
        db.add(
            m.NoticeDecision(
                notice_id=notice.id,
                student_id=sid,
                user_id=member.user_id,
                answer=payload.answer,
                institution_id=member.institution_id,
                school_id=member.school_id,
            )
        )
        audit(db, member, "notices.answer", notice.id)
    db.flush()
    return {
        "message": "Resposta registrada."
        if payload.answer is not None
        else "Leitura registrada."
    }


@router.get("/notices/{item_id}/receipts")
def receipts(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS)
    n = accessible(db, member, item_id)
    targets = db.scalars(
        scoped(m.NoticeRecipient, member).where(m.NoticeRecipient.notice_id == n.id)
    ).all()
    responses = db.scalars(
        scoped(m.NoticeResponse, member).where(m.NoticeResponse.notice_id == n.id)
    ).all()
    return [
        {
            "student_id": t.student_id,
            "student": find(db, m.Student, t.student_id, member).name,
            "read": any(
                r.student_id == t.student_id and r.viewer_role == "guardian"
                for r in responses
            ),
            "any_read": any(r.student_id == t.student_id for r in responses),
            "responses": [
                {
                    "user": db.get(m.User, r.user_id).name,
                    "viewer_role": r.viewer_role,
                    "read_at": r.read_at,
                    "answer": r.answer,
                    "answered_at": r.answered_at,
                }
                for r in responses
                if r.student_id == t.student_id
            ],
        }
        for t in targets
    ]


@router.post("/notices/{item_id}/archive")
def archive(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS)
    accessible(db, member, item_id)
    n = find(db, m.Notice, item_id, member, lock=True)
    n.archived = True
    audit(db, member, "notices.archive", n.id)
    return {"message": "Comunicado arquivado; registros de resposta preservados."}

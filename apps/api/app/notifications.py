"""Private in-app reminders. External message delivery is intentionally separate."""

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import select, or_, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import audit, scoped
from .security import membership, MANAGERS
from .community import student_ids, medical_ids
from .services import data_for, department_rules
from .mfa import cipher

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Lembretes internos"]
)


class DismissIn(Schema):
    key: str = Field(min_length=3, max_length=200)


def mark(db, member, key):
    db.execute(
        insert(m.NotificationDismissal)
        .values(
            institution_id=member.institution_id,
            school_id=member.school_id,
            user_id=member.user_id,
            key=key,
        )
        .on_conflict_do_nothing(
            index_elements=["institution_id", "school_id", "user_id", "key"]
        )
    )


def mark_thread(db, member, record_id):
    latest = db.scalar(
        scoped(m.ServiceEvent, member)
        .where(
            m.ServiceEvent.record_id == str(record_id),
            m.ServiceEvent.action == "comment",
        )
        .order_by(m.ServiceEvent.created_at.desc(), m.ServiceEvent.id.desc())
    )
    if latest and latest.actor_id != member.user_id:
        mark(db, member, "message:" + str(record_id) + ":" + latest.id)


def reminders(db, member):
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("America/Sao_Paulo")).date()
    own = student_ids(db, member)
    health = medical_ids(db, member)
    items = []

    def add(key, title, message, destination):
        items.append(
            {"key": key, "title": title, "message": message, "destination": destination}
        )

    if member.role in {"guardian", "student", "teacher"}:
        normal = select(m.NoticeRecipient.notice_id).where(
            m.NoticeRecipient.student_id.in_(own)
        )
        medical = select(m.NoticeRecipient.notice_id).where(
            m.NoticeRecipient.student_id.in_(health)
        )
        notices = db.scalars(
            scoped(m.Notice, member)
            .where(
                m.Notice.archived.is_(False),
                or_(
                    and_(m.Notice.purpose != "medication", m.Notice.id.in_(normal)),
                    and_(m.Notice.purpose == "medication", m.Notice.id.in_(medical)),
                ),
            )
            .order_by(m.Notice.published_at.desc())
        ).all()
        for n in notices:
            audience = health if n.purpose == "medication" else own
            targets = list(
                db.scalars(
                    scoped(m.NoticeRecipient, member).where(
                        m.NoticeRecipient.notice_id == n.id,
                        m.NoticeRecipient.student_id.in_(audience),
                    )
                )
            )
            read = set(
                db.scalars(
                    scoped(m.NoticeResponse, member)
                    .with_only_columns(m.NoticeResponse.student_id)
                    .where(
                        m.NoticeResponse.notice_id == n.id,
                        m.NoticeResponse.user_id == member.user_id,
                    )
                )
            )
            if any(t.student_id not in read for t in targets):
                add(
                    "notice:" + n.id,
                    cipher().decrypt(n.title.encode()).decode()
                    if n.body_encrypted
                    else n.title,
                    "Comunicado aguardando confirmação de leitura.",
                    "notices",
                )
    if member.role == "guardian":
        stmt = scoped(m.ServiceRecord, member).where(
            m.ServiceRecord.student_id.in_(own)
        )
    elif member.role == "director":
        stmt = scoped(m.ServiceRecord, member)
    elif member.role in {"secretary", "coordinator"}:
        permitted = {"tickets", "renewals", "library", "pickup_queue"} | (
            {"finance"} if member.role == "secretary" else set()
        )
        stmt = scoped(m.ServiceRecord, member).where(
            or_(
                m.ServiceRecord.module.in_(permitted),
                and_(
                    m.ServiceRecord.module == "medication",
                    m.ServiceRecord.student_id.in_(health),
                ),
            )
        )
    elif member.role == "teacher":
        stmt = scoped(m.ServiceRecord, member).where(
            m.ServiceRecord.module == "medication",
            m.ServiceRecord.student_id.in_(health),
        )
    else:
        stmt = None
    if stmt is not None:
        records = list(
            db.scalars(
                stmt.where(
                    m.ServiceRecord.module.in_(
                        [
                            "tickets",
                            "renewals",
                            "library",
                            "finance",
                            "medication",
                            "pickup_queue",
                        ]
                    )
                )
            )
        )
        events = list(
            db.scalars(
                scoped(m.ServiceEvent, member)
                .where(
                    m.ServiceEvent.record_id.in_([r.id for r in records]),
                    m.ServiceEvent.action == "comment",
                )
                .order_by(m.ServiceEvent.created_at.desc(), m.ServiceEvent.id.desc())
            )
        )
        latest = {}
        for event in events:
            latest.setdefault(event.record_id, event)
        departments = {}
        names = dict(
            db.execute(
                scoped(m.Student, member)
                .with_only_columns(m.Student.id, m.Student.name)
                .where(
                    m.Student.id.in_({r.student_id for r in records if r.student_id})
                )
            ).all()
        )
        for r in records:
            if r.module == "tickets":
                department = r.data["department"]
                if department not in departments:
                    departments[department] = department_rules(db, member, department)
                rules = departments[department]
                if member.role in MANAGERS and (
                    member.role not in rules["roles"] or not rules["open"]
                ):
                    continue
            if (
                r.module == "medication"
                and member.role not in {"guardian", "director"}
                and r.student_id not in health
            ):
                continue
            data = data_for(r)
            student = names.get(r.student_id, "")
            event = latest.get(r.id)
            if event and event.actor_id != member.user_id:
                add(
                    "message:" + r.id + ":" + event.id,
                    "Nova mensagem · " + student,
                    "Há um novo acompanhamento em " + r.title + ".",
                    "services:" + r.module,
                )
            if r.module == "finance" and r.status == "pending":
                due = date.fromisoformat(data["due_date"])
                difference = (today - due).days
                if difference >= -5:
                    add(
                        "finance:"
                        + r.id
                        + ":"
                        + (
                            "-5"
                            if difference < 0
                            else "0"
                            if difference < 3
                            else "3"
                            if difference < 7
                            else "7"
                            if difference < 15
                            else "15"
                        ),
                        "Mensalidade / conta · " + student,
                        "Vencimento em "
                        + due.strftime("%d/%m/%Y")
                        + (
                            " · em atraso"
                            if difference > 0
                            else " · lembrete de vencimento"
                        ),
                        "services:" + r.module,
                    )
            if (
                r.module == "library"
                and r.status == "loaned"
                and date.fromisoformat(data["due_date"]) < today
            ):
                add(
                    "library:" + r.id,
                    "Devolução de livro · " + student,
                    "Empréstimo com devolução prevista para "
                    + date.fromisoformat(data["due_date"]).strftime("%d/%m/%Y")
                    + ".",
                    "services:" + r.module,
                )
            if (
                r.module == "pickup_queue"
                and r.status == "called"
                and member.role == "guardian"
            ):
                add(
                    "queue:" + r.id,
                    "Aluno chamado · " + student,
                    "A equipe chamou o aluno. Aguarde a conferência presencial.",
                    "access-control",
                )
            if (
                r.module == "medication"
                and r.status == "scheduled"
                and datetime.fromisoformat(data["scheduled_at"]) <= now
            ):
                add(
                    "medication:" + r.id,
                    "Registro de cuidado previsto · " + student,
                    "Há um horário de medicação programado aguardando conferência da equipe autorizada.",
                    "services:" + r.module,
                )
    if member.role in MANAGERS | {"teacher", "guardian"}:
        slots = scoped(m.MeetingSlot, member).where(
            m.MeetingSlot.student_id.is_not(None),
            m.MeetingSlot.starts_at >= now,
            m.MeetingSlot.starts_at < now + timedelta(days=1),
        )
        if member.role == "guardian":
            slots = slots.where(
                m.MeetingSlot.booked_by == member.user_id,
                m.MeetingSlot.student_id.in_(own),
            )
        elif member.role == "teacher":
            slots = slots.where(m.MeetingSlot.teacher_id == member.teacher_id)
        for slot in db.scalars(slots):
            add(
                "meeting:" + slot.id,
                "Reunião agendada",
                "Horário: "
                + slot.starts_at.astimezone(ZoneInfo("America/Sao_Paulo")).strftime(
                    "%d/%m/%Y %H:%M"
                )
                + ".",
                "meetings",
            )
    dismissed = set(
        db.scalars(
            scoped(m.NotificationDismissal, member)
            .with_only_columns(m.NotificationDismissal.key)
            .where(m.NotificationDismissal.user_id == member.user_id)
        )
    )
    return [item for item in items if item["key"] not in dismissed]


@router.get("/notifications")
def notifications(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
):
    items = reminders(db, member)
    audit(db, member, "notifications.read", member.school_id)
    return {"count": len(items), "items": items[offset : offset + limit]}


@router.post("/notifications/dismiss")
def dismiss(
    payload: DismissIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    if not any(n["key"] == payload.key for n in reminders(db, member)):
        return {"message": "Lembrete já dispensado ou indisponível."}
    mark(db, member, payload.key)
    return {"message": "Lembrete dispensado."}

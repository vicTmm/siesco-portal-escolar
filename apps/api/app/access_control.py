"""Short-lived school identifiers and one-use pickup permissions; staff verifies identity."""

import base64
import io
import json
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from secrets import token_urlsafe
from uuid import UUID
import qrcode
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find, create, audit
from .security import membership, permit, hash_token
from .learning import family_access
from .community import student_ids
from .services import data_for, access_record, image_consent, serialize
from .mfa import cipher

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Identificação e portaria"]
)
STAFF = {"director", "secretary"}


class PickupIn(Schema):
    student_id: UUID
    person: str = Field(min_length=3, max_length=160)
    relationship: str = Field(min_length=2, max_length=100)
    valid_until: datetime
    consent_notice: UUID


class TokenIn(Schema):
    code: str = Field(min_length=20, max_length=4096)
    identity_verified: bool = False


class LocationIn(Schema):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    radius_m: int = Field(ge=50, le=2000)


class ArrivalIn(Schema):
    student_id: UUID
    vehicle: str = Field(min_length=2, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    accuracy_m: float | None = Field(default=None, ge=0, le=200, allow_inf_nan=False)


class ReleaseIn(Schema):
    version: int = Field(ge=1)
    identity_verified: bool
    note: str = Field(min_length=3, max_length=1000)


def qr(value):
    output = io.BytesIO()
    qrcode.make(value).save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode()


def active_student(db, member, student_id):
    day = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    eligible = db.scalar(
        scoped(m.Enrollment, member).where(
            m.Enrollment.student_id == str(student_id),
            m.Enrollment.status == "active",
            m.Enrollment.academic_year == day.year,
        )
    )
    if not eligible:
        raise HTTPException(409, "Aluno sem matrícula ativa no calendário atual.")
    return find(db, m.Student, student_id, member)


def guardian_current(db, member, record):
    owner = db.get(m.User, record.owner_id)
    if not owner or not owner.active:
        return False
    memberships = db.scalars(
        select(m.Membership)
        .where(
            m.Membership.user_id == owner.id,
            m.Membership.institution_id == member.institution_id,
            m.Membership.school_id == member.school_id,
        )
        .with_for_update()
    ).all()
    for p in memberships:
        if p.role in STAFF:
            return True
        if p.role == "guardian" and db.scalar(
            scoped(m.GuardianLink, member)
            .where(
                m.GuardianLink.guardian_id == p.guardian_id,
                m.GuardianLink.student_id == record.student_id,
                m.GuardianLink.verified.is_(True),
            )
            .with_for_update()
        ):
            return True
    return False


def location(db, member):
    row = db.scalar(
        scoped(m.ServiceRecord, member).where(
            m.ServiceRecord.module == "pickup_location"
        )
    )
    return row.data if row else None


@router.get("/pickup-location")
def get_location(
    member=Depends(membership), db: Session = Depends(database, scope="function")
):
    permit(member, STAFF | {"guardian"})
    return location(db, member)


@router.put("/pickup-location")
def set_location(
    payload: LocationIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    db.scalar(select(m.School).where(m.School.id == member.school_id).with_for_update())
    row = db.scalar(
        scoped(m.ServiceRecord, member).where(
            m.ServiceRecord.module == "pickup_location"
        )
    )
    if row:
        row.data = payload.model_dump()
        row.version += 1
    else:
        create(
            db,
            m.ServiceRecord,
            {
                "module": "pickup_location",
                "title": "Localização da escola",
                "owner_id": member.user_id,
                "data": payload.model_dump(),
                "status": "active",
            },
            member,
        )
    audit(db, member, "pickup.location", member.school_id)
    return payload


@router.post("/school-cards/{student_id}/issue")
def card(
    student_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF | {"guardian", "student"})
    family_access(db, member, student_id)
    student = active_student(db, member, student_id)
    token = (
        cipher()
        .encrypt(
            json.dumps(
                {
                    "student_id": student.id,
                    "institution_id": member.institution_id,
                    "school_id": member.school_id,
                    "membership_id": member.id,
                }
            ).encode()
        )
        .decode()
    )
    audit(db, member, "school_cards.issue", student.id)
    return {
        "student": student.name,
        "school": db.get(m.School, member.school_id).name,
        "code": "SIESCO:CARD:" + token,
        "qr_base64": qr("SIESCO:CARD:" + token),
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=90),
    }


@router.post("/school-cards/check")
def check_card(
    payload: TokenIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    try:
        data = json.loads(
            cipher().decrypt(payload.code.removeprefix("SIESCO:CARD:").encode(), ttl=90)
        )
    except (InvalidToken, ValueError, UnicodeError):
        raise HTTPException(422, "Identificação inválida ou expirada.")
    if (
        data.get("institution_id") != member.institution_id
        or data.get("school_id") != member.school_id
    ):
        raise HTTPException(404, "Identificação de outra unidade.")
    issuer = db.get(m.Membership, data.get("membership_id"))
    user = db.get(m.User, issuer.user_id) if issuer else None
    if (
        not issuer
        or not user
        or not user.active
        or issuer.institution_id != member.institution_id
        or issuer.school_id != member.school_id
        or issuer.role not in STAFF | {"guardian", "student"}
    ):
        raise HTTPException(422, "Acesso emissor revogado.")
    if issuer.role not in STAFF and data["student_id"] not in student_ids(db, issuer):
        raise HTTPException(422, "Vínculo emissor não está mais vigente.")
    student = active_student(db, member, data["student_id"])
    audit(db, member, "school_cards.check", student.id)
    return {
        "student_id": student.id,
        "student": student.name,
        "message": "Identificação escolar válida. Confira a identidade da pessoa presente.",
    }


@router.post("/pickups", status_code=201)
def request_pickup(
    payload: PickupIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF | {"guardian"})
    family_access(db, member, payload.student_id)
    active_student(db, member, payload.student_id)
    if payload.valid_until.tzinfo is None or not datetime.now(
        timezone.utc
    ) < payload.valid_until <= datetime.now(timezone.utc) + timedelta(hours=24):
        raise HTTPException(
            422, "Defina validade futura de até 24 horas, com fuso horário."
        )
    notice = find(db, m.Notice, payload.consent_notice, member)
    if notice.kind != "authorization" or notice.purpose != "pickup":
        raise HTTPException(
            422, "Selecione uma autorização específica de retirada por terceiro."
        )
    record = create(
        db,
        m.ServiceRecord,
        {
            "module": "pickup",
            "title": "Retirada por terceiro",
            "student_id": str(payload.student_id),
            "owner_id": member.user_id,
            "data": {
                "encrypted": cipher()
                .encrypt(
                    json.dumps(
                        {
                            "person": payload.person,
                            "relationship": payload.relationship,
                            "valid_until": payload.valid_until.isoformat(),
                            "consent_notice": str(payload.consent_notice),
                        }
                    ).encode()
                )
                .decode()
            },
            "status": "expected",
        },
        member,
    )
    if not image_consent(db, member, record, "pickup", lock=True):
        raise HTTPException(
            409,
            "A autorização específica precisa de resposta positiva vigente do responsável.",
        )
    return serialize(db, member, record)


@router.get("/pickups")
def pickups(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, STAFF | {"guardian"})
    stmt = scoped(m.ServiceRecord, member).where(m.ServiceRecord.module == "pickup")
    if member.role == "guardian":
        stmt = stmt.where(m.ServiceRecord.student_id.in_(student_ids(db, member)))
    audit(db, member, "pickup.read", member.school_id)
    return [
        serialize(db, member, r)
        for r in db.scalars(
            stmt.order_by(m.ServiceRecord.created_at.desc(), m.ServiceRecord.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/pickups/{item_id}/code")
def generate_code(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF | {"guardian"})
    record = access_record(db, member, item_id)
    record = find(db, m.ServiceRecord, record.id, member, lock=True)
    if record.module != "pickup" or record.status != "expected":
        raise HTTPException(409, "Solicitação não está disponível para liberação.")
    data = data_for(record)
    expires = datetime.fromisoformat(data["valid_until"])
    if (
        expires <= datetime.now(timezone.utc)
        or not guardian_current(db, member, record)
        or not image_consent(db, member, record, "pickup", lock=True)
    ):
        raise HTTPException(409, "Autorização expirada, retirada ou vínculo revogado.")
    if not db.scalar(
        scoped(m.PrivateAttachment, member).where(
            m.PrivateAttachment.record_id == record.id
        )
    ):
        raise HTTPException(
            409, "Anexe o documento da pessoa autorizada antes de gerar o código."
        )
    token = token_urlsafe(32)
    create(
        db,
        m.PickupCode,
        {
            "record_id": record.id,
            "token_hash": hash_token(token),
            "expires_at": expires,
        },
        member,
    )
    return {
        "code": "SIESCO:PICKUP:" + token,
        "qr_base64": qr("SIESCO:PICKUP:" + token),
        "expires_at": expires,
    }


@router.post("/pickups/check")
def release(
    payload: TokenIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    if not payload.identity_verified:
        raise HTTPException(
            422, "Confirme a conferência presencial da identidade e do documento."
        )
    code = db.scalar(
        scoped(m.PickupCode, member).where(
            m.PickupCode.token_hash
            == hash_token(payload.code.removeprefix("SIESCO:PICKUP:"))
        )
    )
    if not code:
        raise HTTPException(404, "Código não encontrado.")
    record = find(db, m.ServiceRecord, code.record_id, member, lock=True)
    if (
        code.consumed_at
        or record.status != "expected"
        or code.expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(409, "Código usado, expirado ou solicitação cancelada.")
    active_student(db, member, record.student_id)
    if not guardian_current(db, member, record) or not image_consent(
        db, member, record, "pickup"
    ):
        raise HTTPException(
            409, "A autorização ou o vínculo do responsável não está mais vigente."
        )
    code.consumed_at = datetime.now(timezone.utc)
    record.status = "released"
    record.version += 1
    create(
        db,
        m.ServiceEvent,
        {
            "record_id": record.id,
            "actor_id": member.user_id,
            "action": "pickup.release",
            "data": {
                "encrypted": cipher()
                .encrypt(
                    json.dumps(
                        {
                            "note": "Identidade e documento conferidos presencialmente pela equipe."
                        }
                    ).encode()
                )
                .decode()
            },
        },
        member,
    )
    return {
        "student": find(db, m.Student, record.student_id, member).name,
        "person": data_for(record)["person"],
        "message": "Retirada registrada. Este código não pode ser reutilizado.",
    }


@router.post("/pickup-queue", status_code=201)
def arrival(
    payload: ArrivalIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF | {"guardian"})
    family_access(db, member, payload.student_id)
    active_student(db, member, payload.student_id)
    find(db, m.Student, payload.student_id, member, lock=True)
    if db.scalar(
        scoped(m.ServiceRecord, member).where(
            m.ServiceRecord.module == "pickup_queue",
            m.ServiceRecord.student_id == str(payload.student_id),
            m.ServiceRecord.status.in_(["waiting", "called"]),
        )
    ):
        raise HTTPException(409, "Aluno já está na fila de saída.")
    method = "manual"
    if payload.latitude is not None or payload.longitude is not None:
        config = location(db, member)
        if (
            not config
            or payload.latitude is None
            or payload.longitude is None
            or payload.accuracy_m is None
        ):
            raise HTTPException(
                422, "Localização da escola ou coordenadas do dispositivo incompletas."
            )
        lat1, lat2 = math.radians(payload.latitude), math.radians(config["latitude"])
        delta = math.radians(config["longitude"] - payload.longitude)
        a = (
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta / 2) ** 2
        )
        distance = 6371000 * 2 * math.asin(min(1, math.sqrt(a)))
        if distance > config["radius_m"]:
            raise HTTPException(
                409, "A localização informada está fora do raio de chegada configurado."
            )
        method = "gps"
    r = create(
        db,
        m.ServiceRecord,
        {
            "module": "pickup_queue",
            "title": "Chegada para retirada",
            "student_id": str(payload.student_id),
            "owner_id": member.user_id,
            "data": {
                "encrypted": cipher()
                .encrypt(
                    json.dumps({"vehicle": payload.vehicle, "method": method}).encode()
                )
                .decode()
            },
            "status": "waiting",
        },
        member,
    )
    return serialize(db, member, r)


@router.get("/pickup-queue")
def queue(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, STAFF | {"guardian"})
    stmt = scoped(m.ServiceRecord, member).where(
        m.ServiceRecord.module == "pickup_queue",
        m.ServiceRecord.status.in_(["waiting", "called"]),
    )
    if member.role == "guardian":
        stmt = stmt.where(m.ServiceRecord.student_id.in_(student_ids(db, member)))
    audit(db, member, "pickup.queue_read", member.school_id)
    return [
        serialize(db, member, r)
        for r in db.scalars(
            stmt.order_by(m.ServiceRecord.created_at, m.ServiceRecord.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/pickup-queue/{item_id}/release")
def release_queue(
    item_id: UUID,
    payload: ReleaseIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    r = find(db, m.ServiceRecord, item_id, member, lock=True)
    if (
        r.module != "pickup_queue"
        or r.status not in {"waiting", "called"}
        or r.version != payload.version
    ):
        raise HTTPException(
            409, "Fila alterada. Recarregue antes de registrar a saída."
        )
    if not payload.identity_verified:
        raise HTTPException(
            422, "Confirme a conferência presencial da pessoa autorizada."
        )
    if not guardian_current(db, member, r):
        raise HTTPException(409, "Vínculo do solicitante revogado.")
    r.status = "released"
    r.version += 1
    create(
        db,
        m.ServiceEvent,
        {
            "record_id": r.id,
            "actor_id": member.user_id,
            "action": "queue.release",
            "data": {
                "encrypted": cipher()
                .encrypt(json.dumps({"note": payload.note}).encode())
                .decode()
            },
        },
        member,
    )
    return {"message": "Saída registrada após conferência presencial."}


@router.post("/school-cards/register-entry", status_code=201)
def register_entry(
    payload: TokenIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    if not payload.identity_verified:
        raise HTTPException(
            422,
            "Confirme a conferência presencial da identidade antes de registrar a entrada.",
        )
    result = check_card(payload, member, db)
    student = find(db, m.Student, result["student_id"], member, lock=True)
    token_hash = hash_token(
        base64.urlsafe_b64encode(
            base64.urlsafe_b64decode(payload.code.removeprefix("SIESCO:CARD:"))
        ).decode()
    )
    existing = db.scalar(
        scoped(m.ServiceRecord, member).where(
            m.ServiceRecord.module == "access",
            m.ServiceRecord.data["card_hash"].as_string() == token_hash,
        )
    )
    if existing:
        return {
            "id": existing.id,
            "student": student.name,
            "message": "Esta entrada já foi registrada.",
        }
    record = create(
        db,
        m.ServiceRecord,
        {
            "module": "access",
            "title": "Entrada por identificação escolar",
            "student_id": student.id,
            "owner_id": member.user_id,
            "data": {
                "authorized_person": student.name,
                "relationship": "Aluno identificado pela equipe",
                "notes": "Entrada confirmada presencialmente.",
                "card_hash": token_hash,
            },
            "status": "entered",
        },
        member,
    )
    create(
        db,
        m.ServiceEvent,
        {
            "record_id": record.id,
            "actor_id": member.user_id,
            "action": "transition",
            "data": {
                "from": "expected",
                "to": "entered",
                "note": "Identidade conferida pela equipe.",
            },
        },
        member,
    )
    return {
        "id": record.id,
        "student": student.name,
        "message": "Entrada registrada após conferência presencial.",
    }

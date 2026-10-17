"""Interest-free proposal simulation and transactional manual receivable restructuring."""

import calendar
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import find, create
from .security import membership, permit
from .learning import family_access

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Negociação de recebíveis"]
)


class SimulationIn(Schema):
    student_id: UUID
    receivable_ids: list[UUID] = Field(min_length=1, max_length=50)
    installments: int = Field(ge=1, le=24)
    first_due: date


class ProposalIn(SimulationIn):
    note: str = Field(min_length=3, max_length=2000)


def month(day, offset):
    year = day.year + (day.month - 1 + offset) // 12
    mth = (day.month - 1 + offset) % 12 + 1
    return date(year, mth, min(day.day, calendar.monthrange(year, mth)[1]))


def simulate(db, member, payload):
    permit(member, {"director", "secretary", "guardian"})
    family_access(db, member, payload.student_id)
    if len(set(payload.receivable_ids)) != len(payload.receivable_ids):
        raise HTTPException(422, "Selecione contas distintas.")
    if (
        payload.first_due < datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        or payload.first_due.year > 2100
    ):
        raise HTTPException(
            422, "Defina o primeiro vencimento a partir de hoje e até 2100."
        )
    records = []
    for identifier in payload.receivable_ids:
        r = find(db, m.ServiceRecord, identifier, member)
        if (
            r.module != "finance"
            or r.student_id != str(payload.student_id)
            or r.status != "pending"
        ):
            raise HTTPException(
                409, "Uma das contas não está mais disponível para negociação."
            )
        records.append(r)
    total = sum(int(r.data["amount_cents"]) for r in records)
    if total < payload.installments:
        raise HTTPException(
            422, "O valor total é muito baixo para essa quantidade de parcelas."
        )
    base, remainder = divmod(total, payload.installments)
    return {
        "principal_cents": total,
        "total_cents": total,
        "interest_percent": "0",
        "receivables": [
            {
                "id": r.id,
                "version": r.version,
                "amount_cents": int(r.data["amount_cents"]),
            }
            for r in records
        ],
        "schedule": [
            {
                "number": n + 1,
                "due_date": month(payload.first_due, n).isoformat(),
                "amount_cents": base + (1 if n < remainder else 0),
            }
            for n in range(payload.installments)
        ],
    }


@router.post("/negotiations/simulate")
def preview(
    payload: SimulationIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    return simulate(db, member, payload)


@router.post("/negotiations/propose", status_code=201)
def propose(
    payload: ProposalIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    quote = simulate(db, member, payload)
    record = create(
        db,
        m.ServiceRecord,
        {
            "module": "agreements",
            "title": "Proposta de parcelamento",
            "student_id": str(payload.student_id),
            "owner_id": member.user_id,
            "data": {
                "amount_cents": str(quote["total_cents"]),
                "installments": str(payload.installments),
                "notes": payload.note,
                "schedule": json.dumps(quote["schedule"]),
                "sources": json.dumps(quote["receivables"]),
            },
            "status": "submitted",
        },
        member,
    )
    return {
        "id": record.id,
        "message": "Proposta enviada para análise da escola. As contas permanecem inalteradas até aprovação.",
    }


def approve_proposal(db, member, record):
    permit(member, {"director", "secretary"})
    if "sources" not in record.data:
        return
    sources = json.loads(record.data["sources"])
    schedule = json.loads(record.data["schedule"])
    locked = []
    for source in sorted(sources, key=lambda s: s["id"]):
        r = find(db, m.ServiceRecord, source["id"], member, lock=True)
        if (
            r.module != "finance"
            or r.student_id != record.student_id
            or r.status != "pending"
            or r.version != source["version"]
            or int(r.data["amount_cents"]) != source["amount_cents"]
        ):
            raise HTTPException(
                409,
                "As contas originais mudaram. Peça uma nova simulação antes de aprovar.",
            )
        locked.append(r)
    if sum(int(r.data["amount_cents"]) for r in locked) != sum(
        p["amount_cents"] for p in schedule
    ):
        raise HTTPException(409, "Parcelas e contas originais não estão conciliadas.")
    for r in locked:
        r.status = "restructured"
        r.version += 1
        create(
            db,
            m.ServiceEvent,
            {
                "record_id": r.id,
                "actor_id": member.user_id,
                "action": "restructure",
                "data": {
                    "from": "pending",
                    "to": "restructured",
                    "note": "Substituída por parcelas do acordo " + record.id[:8],
                },
            },
            member,
        )
    created = []
    for installment in schedule:
        item = create(
            db,
            m.ServiceRecord,
            {
                "module": "finance",
                "title": f"Acordo {record.id[:8]} · parcela {installment['number']}/{len(schedule)}",
                "student_id": record.student_id,
                "owner_id": member.user_id,
                "data": {
                    "amount_cents": str(installment["amount_cents"]),
                    "due_date": installment["due_date"],
                    "reference": "Acordo " + record.id,
                    "notes": "Parcela gerada por aprovação da escola; cobrança e baixa manuais.",
                },
                "status": "pending",
            },
            member,
        )
        created.append(item.id)
    record.data = {**record.data, "created_receivables": json.dumps(created)}

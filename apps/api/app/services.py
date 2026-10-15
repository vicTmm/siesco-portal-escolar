"""Versioned school workflows. Financial settlement and operational logs are manual."""

import json
import re
import unicodedata
from datetime import time
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find, create, audit
from .security import membership, permit, MANAGERS
from .community import student_ids
from .mfa import cipher

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Serviços escolares"]
)
# Field definitions are shared with the client; every stored payload is validated here.
MODULES = {
    "contract_templates": (
        "Modelos de minuta contratual",
        {"clauses": "Texto da minuta", "notes": "Observações de revisão"},
        ["draft", "published", "archived"],
    ),
    "office_hours": (
        "Setores e expediente",
        {
            "department": "Setor",
            "weekdays": "Dias da semana (1 = segunda, 7 = domingo)",
            "opens": "Início do expediente",
            "closes": "Fim do expediente",
            "roles": "Perfis da equipe (Diretor, Secretaria, Coordenação)",
        },
        ["active", "archived"],
    ),
    "calendar": (
        "Calendário de eventos",
        {
            "starts_at": "Início",
            "ends_at": "Fim",
            "location": "Local",
            "description": "Descrição",
        },
        ["draft", "published", "archived"],
    ),
    "pickup": (
        "Retirada por terceiro",
        {
            "person": "Pessoa autorizada",
            "relationship": "Vínculo",
            "valid_until": "Validade",
            "consent_notice": "Autorização de retirada",
        },
        ["expected", "released", "cancelled"],
    ),
    "pickup_queue": (
        "Fila de saída",
        {"vehicle": "Veículo", "method": "Forma de chegada"},
        ["waiting", "called", "released", "cancelled"],
    ),
    "pei_goals": (
        "Metas do PEI",
        {
            "pei_id": "Plano PEI",
            "goal": "Objetivo observável",
            "unit": "Unidade da medida",
            "target": "Meta numérica",
            "current": "Valor atual",
            "due_date": "Prazo",
            "evidence": "Critério de evidência",
        },
        ["draft", "published", "archived"],
    ),
    "care_events": (
        "Atendimentos de enfermaria",
        {
            "occurred_at": "Data e hora",
            "description": "Ocorrência relatada",
            "care": "Cuidado realizado pelo profissional",
            "family_contact": "Contato com a família",
        },
        ["draft", "published", "archived"],
    ),
    "medication": (
        "Autorizações e registros de medicação",
        {
            "instructions": "Orientações exatas da prescrição",
            "scheduled_at": "Data e hora previstas",
            "consent_notice": "Código da autorização de medicação",
            "notes": "Observações da família",
        },
        ["submitted", "scheduled", "administered", "cancelled"],
    ),
    "moments": (
        "Momentos da escola",
        {
            "caption": "Descrição do momento",
            "consent_notice": "Código da autorização de imagem",
        },
        ["published", "archived"],
    ),
    "store": (
        "Loja e eventos",
        {
            "item": "Produto ou evento",
            "quantity": "Quantidade",
            "amount_cents": "Valor total",
            "notes": "Observações",
        },
        ["requested", "approved", "delivered", "cancelled"],
    ),
    "agreements": (
        "Propostas de negociação",
        {
            "amount_cents": "Valor proposto",
            "installments": "Quantidade de parcelas",
            "notes": "Proposta da família",
        },
        ["submitted", "review", "approved", "rejected"],
    ),
    "knowledge": (
        "Regimento e orientações",
        {"content": "Orientação institucional", "source": "Referência do documento"},
        ["draft", "published", "archived"],
    ),
    "tickets": (
        "Atendimento às famílias",
        {"department": "Setor", "description": "Solicitação"},
        ["open", "in_progress", "resolved"],
    ),
    "renewals": (
        "Matrícula e rematrícula",
        {
            "request_type": "Modalidade",
            "academic_year": "Ano pretendido",
            "contact": "Contato atualizado",
            "address": "Endereço",
            "notes": "Observações",
        },
        ["submitted", "review", "approved", "rejected"],
    ),
    "leads": (
        "Captação e interessados",
        {"contact": "Contato", "grade": "Série de interesse", "notes": "Observações"},
        ["new", "contacted", "enrolled", "closed"],
    ),
    "plans": (
        "Planejamento pedagógico",
        {
            "date": "Data da aula",
            "bncc": "Códigos de habilidades BNCC",
            "objectives": "Objetivos",
            "activities": "Atividades",
            "resources": "Recursos",
        },
        ["draft", "published", "archived"],
    ),
    "questions": (
        "Banco de questões",
        {
            "subject": "Disciplina",
            "prompt": "Enunciado",
            "options": "Alternativas",
            "answer": "Gabarito",
            "explanation": "Justificativa",
        },
        ["draft", "ready", "archived"],
    ),
    "pei": (
        "Plano educacional individualizado",
        {
            "goals": "Objetivos",
            "adaptations": "Adaptações",
            "strategies": "Estratégias",
            "progress": "Acompanhamento",
        },
        ["draft", "published", "archived"],
    ),
    "health": (
        "Cuidados e saúde",
        {
            "allergies": "Alergias e restrições",
            "care": "Cuidados informados pela família",
            "contact": "Contato de emergência",
        },
        ["active", "archived"],
    ),
    "books": (
        "Acervo da biblioteca",
        {
            "author": "Autor",
            "isbn": "ISBN (quando disponível)",
            "shelf": "Localização / código do exemplar",
        },
        ["active", "archived"],
    ),
    "library": (
        "Biblioteca e empréstimos",
        {
            "book": "Livro / exemplar",
            "due_date": "Data de devolução",
            "notes": "Observações",
        },
        ["loaned", "returned", "lost"],
    ),
    "transport": (
        "Transporte escolar",
        {
            "route": "Rota",
            "vehicle": "Veículo",
            "driver": "Motorista",
            "stop": "Ponto",
            "notes": "Observações",
        },
        ["scheduled", "boarded", "delivered", "cancelled"],
    ),
    "finance": (
        "Contas a receber",
        {
            "amount_cents": "Valor",
            "due_date": "Vencimento",
            "reference": "Referência",
            "notes": "Observações",
        },
        ["pending", "paid", "cancelled", "restructured"],
    ),
    "canteen": (
        "Consumos da cantina",
        {
            "amount_cents": "Valor",
            "items": "Itens consumidos",
            "notes": "Observações",
        },
        ["recorded", "settled", "cancelled"],
    ),
    "access": (
        "Entrada e saída",
        {
            "authorized_person": "Pessoa autorizada",
            "relationship": "Vínculo",
            "notes": "Observações",
        },
        ["expected", "entered", "released", "cancelled"],
    ),
    "lost_found": (
        "Achados e perdidos",
        {
            "description": "Descrição do objeto",
            "location": "Local",
            "notes": "Observações",
        },
        ["found", "claimed", "donated"],
    ),
}
SENSITIVE = {"pei", "health", "pei_goals", "care_events", "medication"}
PRIVATE_TYPES = SENSITIVE | {"pickup", "pickup_queue"}


def sensitive_category(module):
    return "pei" if module.startswith("pei") else "health"


FAMILY_CREATE = {
    "tickets",
    "renewals",
    "store",
    "agreements",
    "library",
    "medication",
    "pickup",
    "pickup_queue",
}
FAMILY_READ = FAMILY_CREATE | {
    "office_hours",
    "calendar",
    "pei_goals",
    "care_events",
    "books",
    "moments",
    "knowledge",
    "pei",
    "health",
    "library",
    "transport",
    "finance",
    "canteen",
    "access",
    "lost_found",
}
TEACHER = {
    "calendar",
    "knowledge",
    "plans",
    "questions",
    "pei",
    "health",
    "pei_goals",
    "care_events",
    "medication",
}
TRANSITIONS = {
    "contract_templates": {"draft": ["published"], "published": ["archived"]},
    "office_hours": {"active": ["archived"]},
    "calendar": {"draft": ["published"], "published": ["archived"]},
    "pickup": {"expected": ["cancelled"]},
    "pickup_queue": {"waiting": ["called", "cancelled"], "called": ["cancelled"]},
    "pei_goals": {"draft": ["published"], "published": ["archived"]},
    "care_events": {"draft": ["published"], "published": ["archived"]},
    "medication": {
        "submitted": ["scheduled", "cancelled"],
        "scheduled": ["administered", "cancelled"],
    },
    "books": {"active": ["archived"]},
    "moments": {"published": ["archived"]},
    "store": {
        "requested": ["approved", "cancelled"],
        "approved": ["delivered", "cancelled"],
    },
    "agreements": {
        "submitted": ["review", "rejected"],
        "review": ["approved", "rejected"],
    },
    "knowledge": {"draft": ["published"], "published": ["archived"]},
    "tickets": {
        "open": ["in_progress", "resolved"],
        "in_progress": ["resolved"],
        "resolved": ["open"],
    },
    "renewals": {
        "submitted": ["review", "rejected"],
        "review": ["approved", "rejected"],
        "rejected": ["review"],
    },
    "leads": {"new": ["contacted", "closed"], "contacted": ["enrolled", "closed"]},
    "plans": {"draft": ["published"], "published": ["archived"]},
    "questions": {"draft": ["ready"], "ready": ["archived"]},
    "pei": {"draft": ["published"], "published": ["archived"]},
    "health": {"active": ["archived"]},
    "library": {
        "reserved": ["loaned", "cancelled"],
        "loaned": ["returned", "lost"],
        "lost": ["returned"],
    },
    "transport": {"scheduled": ["boarded", "cancelled"], "boarded": ["delivered"]},
    "finance": {"pending": ["paid", "cancelled"]},
    "canteen": {"recorded": ["settled", "cancelled"]},
    "access": {"expected": ["entered", "cancelled"], "entered": ["released"]},
    "lost_found": {"found": ["claimed", "donated"]},
}


class RecordIn(Schema):
    title: str = Field(min_length=3, max_length=160)
    student_id: UUID | None = None
    class_id: UUID | None = None
    data: dict[str, str] = Field(max_length=10)


class ChangeIn(Schema):
    version: int = Field(ge=1)
    status: str = Field(max_length=30)
    note: str = Field(min_length=3, max_length=2000)


class CommentIn(Schema):
    text: str = Field(min_length=3, max_length=4000)


class GrantIn(Schema):
    student_id: UUID
    user_id: UUID
    category: str
    active: bool = True


def department_code(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in value if not unicodedata.combining(c)).strip()


def department_rules(db, member, value):
    code = department_code(value)
    settings = list(
        db.scalars(
            scoped(m.ServiceRecord, member)
            .where(m.ServiceRecord.module == "office_hours")
            .order_by(m.ServiceRecord.created_at.desc())
        )
    )
    item = next(
        (r for r in settings if department_code(r.data["department"]) == code), None
    )
    mapping = {
        "diretor": "director",
        "secretaria": "secretary",
        "coordenacao": "coordinator",
    }
    roles = (
        {mapping.get(department_code(r)) for r in item.data["roles"].split(",")}
        | {"director"}
        if item
        else {"director"}
        | (
            {"secretary"}
            if code in {"secretaria", "financeiro"}
            else {"coordinator"}
            if code in {"coordenacao", "coordenacao pedagogica"}
            else set()
        )
    )
    if not item:
        return {
            "roles": roles,
            "open": True,
            "hours": "Expediente ainda não configurado.",
        }
    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    is_open = (
        item.status == "active"
        and now.isoweekday() in {int(n) for n in item.data["weekdays"].split(",")}
        and time.fromisoformat(item.data["opens"])
        <= now.time().replace(tzinfo=None)
        < time.fromisoformat(item.data["closes"])
    )
    return {
        "roles": roles,
        "open": is_open,
        "hours": item.data["opens"]
        + " às "
        + item.data["closes"]
        + " · dias "
        + item.data["weekdays"]
        + " · horário de Brasília",
    }


def calendar_classes(db, member):
    return (
        scoped(m.Enrollment, member)
        .with_only_columns(m.Enrollment.class_id)
        .where(
            m.Enrollment.student_id.in_(student_ids(db, member)),
            m.Enrollment.status == "active",
        )
    )


def calendar_visible(db, member, record):
    if record.student_id:
        return record.student_id in student_ids(db, member)
    if record.class_id:
        return bool(
            db.scalar(
                calendar_classes(db, member).where(
                    m.Enrollment.class_id == record.class_id
                )
            )
        )
    return True


def definition(module):
    if module not in MODULES:
        raise HTTPException(404, "Serviço não encontrado.")
    return MODULES[module]


def allowed(db, member, module, student_id=None, write=False, record=None, data=None):
    definition(module)
    if module == "contract_templates":
        permit(member, {"director", "secretary"})
        if write:
            permit(member, {"director"})

    if module == "agreements" and member.role == "coordinator":
        raise HTTPException(403, "Negociação restrita à direção e secretaria.")
    if module == "calendar":
        if write:
            permit(member, {"director", "coordinator"})
        elif member.role not in MANAGERS:
            if (
                record
                and record.status == "published"
                and calendar_visible(db, member, record)
            ):
                return
            raise HTTPException(403, "Evento indisponível para este vínculo.")
    if module == "knowledge" and write:
        permit(member, MANAGERS)
    if module == "office_hours":
        if write:
            permit(member, {"director"})
        elif record and record.status == "active":
            return
    if module in {"plans", "questions"} and write and member.role == "secretary":
        raise HTTPException(
            403, "Alteração pedagógica restrita à direção, coordenação e docentes."
        )
    if module == "tickets" and member.role in MANAGERS and member.role != "director":
        department = (record.data if record else data or {}).get("department", "")
        if member.role not in department_rules(db, member, department)["roles"]:
            raise HTTPException(403, "Acesso restrito à equipe deste setor.")

    if (
        module
        in {"finance", "canteen", "leads", "pickup", "pickup_queue", "agreements"}
        and member.role == "coordinator"
    ):
        raise HTTPException(403, "Serviço restrito à direção e secretaria.")
    if module in SENSITIVE:
        if not student_id:
            raise HTTPException(422, "Selecione o aluno para este registro.")
        if member.role == "director":
            return
        if (
            module == "medication"
            and member.role == "guardian"
            and str(student_id) in student_ids(db, member)
        ):
            return
        if (
            not write
            and member.role == "guardian"
            and str(student_id) in student_ids(db, member)
        ):
            return
        if member.role not in MANAGERS | {"teacher"}:
            raise HTTPException(
                403, "Acesso profissional exige um perfil ativo da equipe."
            )
        grant = db.scalar(
            scoped(m.SensitiveGrant, member).where(
                m.SensitiveGrant.student_id == str(student_id),
                m.SensitiveGrant.user_id == member.user_id,
                m.SensitiveGrant.category == sensitive_category(module),
                m.SensitiveGrant.active.is_(True),
            )
        )
        if grant:
            return
        raise HTTPException(
            403, "Acesso a dados sensíveis exige autorização específica da direção."
        )
    if module == "books" and not write and record and record.status == "active":
        return
    if module == "knowledge" and not write and record and record.status == "published":
        return
    if member.role in MANAGERS:
        return
    if member.role == "teacher" and module in TEACHER:
        if record and record.owner_id != member.user_id:
            raise HTTPException(403, "Acesso restrito ao autor.")
        return
    if member.role == "guardian" and module in (
        FAMILY_CREATE if write else FAMILY_READ
    ):
        if student_id and str(student_id) in student_ids(db, member):
            return
    raise HTTPException(403, "Você não tem permissão para este serviço.")


def data_for(record):
    return (
        json.loads(cipher().decrypt(record.data["encrypted"].encode()))
        if record.module in PRIVATE_TYPES
        else record.data
    )


def serialize(db, member, r):
    data = dict(data_for(r))
    if r.module == "access":
        data.pop("card_hash", None)
    proposal = {}
    if r.module == "agreements" and "schedule" in data:
        proposal = {
            "schedule": json.loads(data.pop("schedule")),
            "sources": json.loads(data.pop("sources")),
            "created_receivables": json.loads(data.pop("created_receivables", "[]")),
        }
    return {
        **({"proposal": proposal} if proposal else {}),
        **(
            {
                "department_info": {
                    k: v
                    for k, v in department_rules(db, member, data["department"]).items()
                    if k != "roles"
                }
            }
            if r.module == "tickets"
            else {}
        ),
        "id": r.id,
        "module": r.module,
        "title": r.title,
        "student_id": r.student_id,
        "student": find(db, m.Student, r.student_id, member).name
        if r.student_id
        else None,
        "class_id": r.class_id,
        "data": data,
        "status": r.status,
        "version": r.version,
        "created_at": r.created_at,
    }


@router.get("/services")
def catalog(member=Depends(membership)):
    return [
        {
            "key": key,
            "title": value[0],
            "fields": value[1],
            "statuses": value[2],
            "transitions": TRANSITIONS[key],
        }
        for key, value in MODULES.items()
        if key not in {"pickup", "pickup_queue"}
        if not (
            member.role == "coordinator" and key in {"agreements", "contract_templates"}
        )
        if (
            member.role in MANAGERS
            and not (
                member.role == "coordinator"
                and key
                in {
                    "finance",
                    "canteen",
                    "leads",
                    "pickup",
                    "pickup_queue",
                    "agreements",
                }
            )
        )
        or (member.role == "teacher" and key in TEACHER)
        or (member.role == "guardian" and key in FAMILY_READ)
        or (member.role == "student" and key in {"calendar", "knowledge"})
    ]


@router.get("/services/{module}")
def records(
    module: str,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    definition(module)
    if module == "contract_templates":
        permit(member, {"director", "secretary"})

    if module == "agreements" and member.role == "coordinator":
        raise HTTPException(403, "Negociação restrita à direção e secretaria.")
    if (
        module
        in {"finance", "canteen", "leads", "pickup", "pickup_queue", "agreements"}
        and member.role == "coordinator"
    ):
        raise HTTPException(403, "Serviço restrito à direção e secretaria.")
    stmt = scoped(m.ServiceRecord, member).where(m.ServiceRecord.module == module)
    if module == "calendar" and member.role not in MANAGERS:
        permit(member, {"guardian", "student", "teacher"})
        stmt = stmt.where(
            m.ServiceRecord.status == "published",
            or_(
                m.ServiceRecord.student_id.in_(student_ids(db, member)),
                and_(
                    m.ServiceRecord.student_id.is_(None),
                    or_(
                        m.ServiceRecord.class_id.is_(None),
                        m.ServiceRecord.class_id.in_(calendar_classes(db, member)),
                    ),
                ),
            ),
        )
    elif module == "knowledge" and member.role not in MANAGERS:
        permit(member, {"guardian", "student", "teacher"})
        stmt = stmt.where(m.ServiceRecord.status == "published")
    elif module in SENSITIVE and member.role != "director":
        if member.role == "guardian":
            stmt = stmt.where(
                m.ServiceRecord.student_id.in_(student_ids(db, member)),
                m.ServiceRecord.status == "published"
                if module in {"pei", "pei_goals", "care_events"}
                else m.ServiceRecord.status != "archived",
            )
        else:
            permit(member, MANAGERS | {"teacher"})
            stmt = stmt.where(
                m.ServiceRecord.student_id.in_(
                    scoped(m.SensitiveGrant, member)
                    .with_only_columns(m.SensitiveGrant.student_id)
                    .where(
                        m.SensitiveGrant.user_id == member.user_id,
                        m.SensitiveGrant.category == sensitive_category(module),
                        m.SensitiveGrant.active.is_(True),
                    )
                )
            )
    elif member.role == "teacher" and module in TEACHER:
        stmt = stmt.where(m.ServiceRecord.owner_id == member.user_id)
    elif member.role == "guardian" and module in {"knowledge", "books", "office_hours"}:
        stmt = stmt.where(
            m.ServiceRecord.status
            == ("published" if module == "knowledge" else "active")
        )
    elif member.role == "guardian" and module in FAMILY_READ:
        stmt = stmt.where(m.ServiceRecord.student_id.in_(student_ids(db, member)))
    elif member.role not in MANAGERS:
        raise HTTPException(403, "Serviço indisponível para seu perfil.")
    if module == "tickets" and member.role in MANAGERS and member.role != "director":
        settings = list(
            db.scalars(
                scoped(m.ServiceRecord, member).where(
                    m.ServiceRecord.module == "office_hours"
                )
            )
        )
        candidates = {
            "secretaria",
            "financeiro",
            "coordenacao",
            "coordenação",
            "coordenacao pedagogica",
        } | {r.data["department"] for r in settings}
        allowed_codes = {
            code
            for code in candidates
            if member.role in department_rules(db, member, code)["roles"]
        }
        stmt = stmt.where(
            func.lower(m.ServiceRecord.data["department"].as_string()).in_(
                allowed_codes
            )
        )
    if module == "calendar" and member.role == "guardian":
        stmt = stmt.where(m.ServiceRecord.status == "published")
    rows = db.scalars(
        stmt.order_by(m.ServiceRecord.created_at.desc(), m.ServiceRecord.id)
        .offset(offset)
        .limit(limit)
    ).all()
    if module in SENSITIVE:
        audit(db, member, "services.sensitive_read", module)
    return [
        serialize(db, member, r)
        for r in rows
        if r.module != "moments"
        or member.role in MANAGERS
        or image_consent(db, member, r)
    ]


@router.post("/services/{module}", status_code=201)
def add_record(
    module: str,
    payload: RecordIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    if module in {"pickup", "pickup_queue"}:
        raise HTTPException(405, "Use o fluxo de portaria para criar este registro.")
    title, fields, statuses = definition(module)
    allowed(db, member, module, payload.student_id, True, data=payload.data)
    if (
        module
        in {
            "renewals",
            "library",
            "transport",
            "finance",
            "canteen",
            "access",
            "moments",
            "store",
            "agreements",
        }
        and not payload.student_id
    ):
        raise HTTPException(422, "Este serviço exige um aluno.")
    if payload.student_id:
        if (
            member.role == "teacher"
            and module not in SENSITIVE
            and str(payload.student_id) not in student_ids(db, member)
        ):
            raise HTTPException(403, "Aluno sem vínculo docente vigente.")
        find(db, m.Student, payload.student_id, member)
    if payload.class_id:
        find(db, m.ClassGroup, payload.class_id, member)
        if member.role == "teacher" and not db.scalar(
            scoped(m.Assignment, member).where(
                m.Assignment.teacher_id == member.teacher_id,
                m.Assignment.class_id == str(payload.class_id),
            )
        ):
            raise HTTPException(403, "Turma sem atribuição docente.")
    if module == "renewals":
        has_enrollment = bool(
            db.scalar(
                scoped(m.Enrollment, member).where(
                    m.Enrollment.student_id == str(payload.student_id)
                )
            )
        )
        payload.data.setdefault(
            "request_type", "renewal" if has_enrollment else "initial"
        )
        if payload.data["request_type"] not in {"initial", "renewal"}:
            raise HTTPException(422, "Selecione matrícula inicial ou rematrícula.")
    if set(payload.data) != set(fields) or any(
        len(v)
        > (30000 if module == "contract_templates" and key == "clauses" else 4000)
        for key, v in payload.data.items()
    ):
        raise HTTPException(
            422,
            "Preencha os campos definidos para este serviço e respeite o tamanho máximo.",
        )
    if "amount_cents" in fields and not re.fullmatch(
        r"[1-9][0-9]{0,9}", payload.data["amount_cents"]
    ):
        raise HTTPException(422, "Informe valor positivo em centavos, sem separadores.")
    for field in ["date", "due_date"]:
        if field in fields:
            try:
                datetime.strptime(payload.data[field], "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    422, "Informe uma data válida no formato AAAA-MM-DD."
                )
    if module in {"store", "agreements"}:
        field = "quantity" if module == "store" else "installments"
        if not re.fullmatch(r"[1-9][0-9]{0,2}", payload.data[field]):
            raise HTTPException(422, "Informe uma quantidade entre 1 e 999.")
    if module == "moments":
        reference = find(db, m.Notice, payload.data["consent_notice"], member)
        if reference.kind != "authorization" or not db.scalar(
            scoped(m.NoticeRecipient, member).where(
                m.NoticeRecipient.notice_id == reference.id,
                m.NoticeRecipient.student_id == str(payload.student_id),
            )
        ):
            raise HTTPException(
                422, "Selecione uma autorização destinada a este aluno."
            )
    if module == "renewals" and not re.fullmatch(
        r"20[0-9]{2}|2100", payload.data["academic_year"]
    ):
        raise HTTPException(422, "Informe ano letivo válido.")
    if module == "library":
        book = find(db, m.ServiceRecord, payload.data["book"], member, lock=True)
        if book.module != "books" or book.status != "active":
            raise HTTPException(422, "Selecione um exemplar ativo do acervo.")
        occupied = db.scalar(
            scoped(m.ServiceRecord, member).where(
                m.ServiceRecord.module == "library",
                m.ServiceRecord.status.in_(["loaned", "reserved"]),
                m.ServiceRecord.data["book"].as_string() == book.id,
            )
        )
        if occupied:
            raise HTTPException(409, "Exemplar já emprestado ou reservado.")
    if module == "office_hours":
        permit(member, {"director"})
        code = department_code(payload.data["department"])
        db.scalar(
            select(m.School).where(m.School.id == member.school_id).with_for_update()
        )
        existing = db.scalar(
            scoped(m.ServiceRecord, member).where(
                m.ServiceRecord.module == "office_hours",
                m.ServiceRecord.status == "active",
                func.lower(m.ServiceRecord.data["department"].as_string()) == code,
            )
        )
        if existing:
            raise HTTPException(
                409,
                "Já existe expediente ativo para este setor. Arquive o anterior para substituir.",
            )
        try:
            days = [int(n.strip()) for n in payload.data["weekdays"].split(",")]
            if (
                not days
                or len(set(days)) != len(days)
                or any(n not in range(1, 8) for n in days)
            ):
                raise ValueError()
            if not re.fullmatch(
                r"\d{2}:\d{2}", payload.data["opens"]
            ) or not re.fullmatch(r"\d{2}:\d{2}", payload.data["closes"]):
                raise ValueError()
            if time.fromisoformat(payload.data["opens"]) >= time.fromisoformat(
                payload.data["closes"]
            ):
                raise ValueError()
            if any(
                department_code(r) not in {"diretor", "secretaria", "coordenacao"}
                for r in payload.data["roles"].split(",")
            ):
                raise ValueError()
        except ValueError:
            raise HTTPException(
                422,
                "Confira dias, horários e os perfis Diretor, Secretaria e Coordenação.",
            )
        payload.data["department"] = code
        payload.data["weekdays"] = ",".join(map(str, days))
    if module == "calendar":
        try:
            start = datetime.fromisoformat(payload.data["starts_at"])
            end = datetime.fromisoformat(payload.data["ends_at"])
            if not start.tzinfo or not end.tzinfo or end <= start:
                raise ValueError()
        except ValueError:
            raise HTTPException(422, "Informe início e fim válidos, com fuso horário.")
    if module == "pei_goals":
        plan = find(db, m.ServiceRecord, payload.data["pei_id"], member)
        if (
            plan.module != "pei"
            or plan.student_id != str(payload.student_id)
            or plan.status == "archived"
        ):
            raise HTTPException(422, "Selecione o PEI deste aluno.")
        if any(
            not re.fullmatch(r"[0-9]{1,10}(\.[0-9]{1,4})?", payload.data[k])
            for k in ["target", "current"]
        ):
            raise HTTPException(
                422, "Meta e valor atual devem ser números com até 4 casas decimais."
            )
        try:
            target = Decimal(payload.data["target"])
            current = Decimal(payload.data["current"])
            if (
                not target.is_finite()
                or not current.is_finite()
                or target <= 0
                or current < 0
            ):
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise HTTPException(
                422, "Informe uma meta positiva e um valor atual não negativo."
            )
    if module in {"care_events", "medication"}:
        field = "occurred_at" if module == "care_events" else "scheduled_at"
        try:
            timestamp = datetime.fromisoformat(payload.data[field])
            if not timestamp.tzinfo:
                raise ValueError()
        except ValueError:
            raise HTTPException(422, "Informe data/hora com fuso horário.")
    data = (
        {
            "encrypted": cipher()
            .encrypt(json.dumps(payload.data, ensure_ascii=False).encode())
            .decode()
        }
        if module in PRIVATE_TYPES
        else payload.data
    )
    # Sensitive titles are deliberately generic; clinical/pedagogical notes live only in the encrypted payload.
    r = create(
        db,
        m.ServiceRecord,
        {
            "module": module,
            "title": title if module in PRIVATE_TYPES else payload.title,
            "student_id": str(payload.student_id) if payload.student_id else None,
            "class_id": str(payload.class_id) if payload.class_id else None,
            "owner_id": member.user_id,
            "data": data,
            "status": "reserved"
            if module == "library" and member.role == "guardian"
            else statuses[0],
        },
        member,
    )
    return serialize(db, member, r)


@router.post("/service-records/{item_id}/transition")
def transition(
    item_id: UUID,
    payload: ChangeIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    r = find(db, m.ServiceRecord, item_id, member, lock=True)
    # Families submit requests and comments; acceptance/settlement is a staff operation.
    if member.role == "guardian" and not (
        r.module in {"medication", "pickup", "pickup_queue"}
        and payload.status == "cancelled"
    ):
        raise HTTPException(403, "A mudança de situação é realizada pela escola.")
    allowed(db, member, r.module, r.student_id, True, r)
    if payload.version != r.version:
        raise HTTPException(
            409, "Este registro foi atualizado. Recarregue antes de continuar."
        )
    if payload.status not in TRANSITIONS[r.module].get(r.status, []):
        raise HTTPException(422, "Mudança de situação inválida.")
    if r.module == "books" and payload.status == "archived":
        occupied = db.scalar(
            scoped(m.ServiceRecord, member).where(
                m.ServiceRecord.module == "library",
                m.ServiceRecord.status.in_(["loaned", "reserved"]),
                m.ServiceRecord.data["book"].as_string() == r.id,
            )
        )
        if occupied:
            raise HTTPException(
                409, "Finalize empréstimos e reservas antes de arquivar este exemplar."
            )
    if r.module in {"pickup", "pickup_queue"} and payload.status == "released":
        raise HTTPException(422, "A liberação exige conferência no fluxo de portaria.")
    if r.module == "medication" and payload.status in {"scheduled", "administered"}:
        if not image_consent(db, member, r, "medication", lock=True):
            raise HTTPException(
                409, "É necessária uma autorização de medicação vigente do responsável."
            )
        if not db.scalar(
            scoped(m.PrivateAttachment, member).where(
                m.PrivateAttachment.record_id == r.id,
                m.PrivateAttachment.mime_type == "application/pdf",
            )
        ):
            raise HTTPException(
                409,
                "Anexe a prescrição em PDF antes de programar ou registrar a administração.",
            )
        if payload.status == "administered" and datetime.fromisoformat(
            data_for(r)["scheduled_at"]
        ) > datetime.now(timezone.utc):
            raise HTTPException(409, "O horário previsto ainda não chegou.")
    if r.module == "agreements" and payload.status == "approved":
        from .billing import approve_proposal

        approve_proposal(db, member, r)
    old = r.status
    r.status = payload.status
    r.version += 1
    data = {"from": old, "to": r.status, "note": payload.note}
    if r.module in PRIVATE_TYPES:
        data = {"encrypted": cipher().encrypt(json.dumps(data).encode()).decode()}
    create(
        db,
        m.ServiceEvent,
        {
            "record_id": r.id,
            "action": "transition",
            "actor_id": member.user_id,
            "data": data,
        },
        member,
    )
    audit(db, member, "services.transition", r.id)
    return serialize(db, member, r)


def access_record(db, member, item_id):
    r = find(db, m.ServiceRecord, item_id, member)
    allowed(db, member, r.module, r.student_id, False, r)
    if (
        member.role == "guardian"
        and r.module == "moments"
        and (r.status != "published" or not image_consent(db, member, r))
    ):
        raise HTTPException(404, "Momento indisponível para este aluno.")
    if (
        member.role == "guardian"
        and r.module in {"pei", "pei_goals", "care_events"}
        and r.status != "published"
    ):
        raise HTTPException(404, "Registro não encontrado.")
    return r


@router.get("/service-records/{item_id}/events")
def events(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    r = access_record(db, member, item_id)
    if member.role in {"guardian", "student"} and r.module in {
        "books",
        "office_hours",
        "knowledge",
        "calendar",
    }:
        raise HTTPException(
            403,
            "Este conteúdo disponibiliza documentos publicados, sem conversa interna da equipe.",
        )
    from .notifications import mark_thread

    mark_thread(db, member, r.id)
    result = []
    for event in db.scalars(
        scoped(m.ServiceEvent, member)
        .where(m.ServiceEvent.record_id == r.id)
        .order_by(m.ServiceEvent.created_at, m.ServiceEvent.id)
    ):
        data = (
            json.loads(cipher().decrypt(event.data["encrypted"].encode()))
            if r.module in PRIVATE_TYPES
            else event.data
        )
        result.append(
            {
                "id": event.id,
                "actor": db.get(m.User, event.actor_id).name,
                "action": event.action,
                "data": data,
                "created_at": event.created_at,
            }
        )
    if r.module in PRIVATE_TYPES:
        audit(db, member, "services.sensitive_history", r.id)
    return result


@router.post("/service-records/{item_id}/comments", status_code=201)
def comment(
    item_id: UUID,
    payload: CommentIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS | {"teacher", "guardian"})
    r = access_record(db, member, item_id)
    if member.role == "teacher" and r.module not in TEACHER:
        raise HTTPException(403, "Comentários indisponíveis neste módulo.")
    if member.role == "guardian" and r.module not in FAMILY_CREATE | SENSITIVE:
        raise HTTPException(403, "Comentários indisponíveis neste registro.")
    data = {"text": payload.text}
    if r.module in PRIVATE_TYPES:
        data = {"encrypted": cipher().encrypt(json.dumps(data).encode()).decode()}
    create(
        db,
        m.ServiceEvent,
        {
            "record_id": r.id,
            "action": "comment",
            "actor_id": member.user_id,
            "data": data,
        },
        member,
    )
    return {"message": "Comentário registrado."}


@router.post("/sensitive-grants")
def grant(
    payload: GrantIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director"})
    if payload.category not in {"pei", "health"}:
        raise HTTPException(422, "Categoria inválida.")
    find(db, m.Student, payload.student_id, member)
    target = db.scalar(
        select(m.Membership).where(
            m.Membership.user_id == str(payload.user_id),
            m.Membership.institution_id == member.institution_id,
            m.Membership.school_id == member.school_id,
            m.Membership.role.in_(MANAGERS | {"teacher"}),
        )
    )
    if not target or target.role not in MANAGERS | {"teacher"}:
        raise HTTPException(422, "Selecione um profissional desta escola.")
    # Lock the student to serialize simultaneous grant creation.
    find(db, m.Student, payload.student_id, member, lock=True)
    g = db.scalar(
        scoped(m.SensitiveGrant, member).where(
            m.SensitiveGrant.student_id == str(payload.student_id),
            m.SensitiveGrant.user_id == str(payload.user_id),
            m.SensitiveGrant.category == payload.category,
        )
    )
    if g:
        g.active = payload.active
    else:
        create(db, m.SensitiveGrant, {**payload.model_dump(mode="json")}, member)
    audit(db, member, "services.sensitive_grant", str(payload.student_id))
    return {"message": "Permissão atualizada."}


@router.get("/sensitive-staff")
def staff(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    permit(member, {"director"})
    stmt = (
        select(m.User)
        .join(m.Membership, m.User.id == m.Membership.user_id)
        .where(
            m.Membership.institution_id == member.institution_id,
            m.Membership.school_id == member.school_id,
            m.Membership.role.in_(MANAGERS | {"teacher"}),
        )
        .distinct()
        .order_by(m.User.name, m.User.id)
        .offset(offset)
        .limit(limit)
    )
    return [{"id": u.id, "name": u.name} for u in db.scalars(stmt)]


@router.get("/sensitive-grants")
def grants(
    member=Depends(membership), db: Session = Depends(database, scope="function")
):
    permit(member, {"director"})
    return [
        {
            "id": g.id,
            "student_id": g.student_id,
            "user_id": g.user_id,
            "category": g.category,
            "active": g.active,
        }
        for g in db.scalars(scoped(m.SensitiveGrant, member))
    ]


def image_consent(db, member, record, purpose="image", lock=False):
    reference = data_for(record).get("consent_notice")
    notice_stmt = scoped(m.Notice, member).where(
        m.Notice.id == reference,
        m.Notice.kind == "authorization",
        m.Notice.purpose == purpose,
        m.Notice.archived.is_(False),
    )
    notice = db.scalar(notice_stmt.with_for_update() if lock else notice_stmt)
    if not notice:
        return False
    # Only a currently linked, verified guardian's latest recorded decision is accepted.
    guardians = (
        scoped(m.GuardianLink, member)
        .with_only_columns(m.GuardianLink.guardian_id)
        .where(
            m.GuardianLink.student_id == record.student_id,
            m.GuardianLink.verified.is_(True),
        )
    )
    users = select(m.Membership.user_id).where(
        m.Membership.institution_id == member.institution_id,
        m.Membership.school_id == member.school_id,
        m.Membership.role == "guardian",
        m.Membership.guardian_id.in_(guardians),
    )
    responses = list(
        db.scalars(
            scoped(m.NoticeResponse, member).where(
                m.NoticeResponse.notice_id == reference,
                m.NoticeResponse.student_id == record.student_id,
                m.NoticeResponse.user_id.in_(users),
            )
        )
    )
    return (
        bool(responses)
        and any(r.answer == "yes" for r in responses)
        and not any(r.answer in {"no", "withdraw"} for r in responses)
    )


class ProgressIn(Schema):
    version: int = Field(ge=1)
    current: str = Field(pattern=r"^[0-9]{1,10}(\.[0-9]{1,4})?$", max_length=15)
    note: str = Field(min_length=3, max_length=2000)


@router.post("/pei-goals/{item_id}/progress")
def progress(
    item_id: UUID,
    payload: ProgressIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    r = find(db, m.ServiceRecord, item_id, member, lock=True)
    if r.module != "pei_goals":
        raise HTTPException(404, "Meta não encontrada.")
    permit(member, MANAGERS | {"teacher"})
    allowed(db, member, r.module, r.student_id, True, r)
    if r.status == "archived" or r.version != payload.version:
        raise HTTPException(
            409, "Meta arquivada ou alterada. Recarregue antes de registrar progresso."
        )
    data = data_for(r)
    previous = data["current"]
    data["current"] = payload.current
    r.data = {"encrypted": cipher().encrypt(json.dumps(data).encode()).decode()}
    r.version += 1
    event = {"from": previous, "to": payload.current, "note": payload.note}
    create(
        db,
        m.ServiceEvent,
        {
            "record_id": r.id,
            "action": "progress",
            "actor_id": member.user_id,
            "data": {
                "encrypted": cipher().encrypt(json.dumps(event).encode()).decode()
            },
        },
        member,
    )
    return serialize(db, member, r)

"""Unsigned contract drafts using only school-authored terms and verified family data."""

import re
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find
from .security import membership, permit
from .documents import save_document

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Minutas contratuais"]
)


class DraftIn(Schema):
    template_id: UUID
    student_id: UUID
    guardian_id: UUID
    academic_year: int = Field(ge=2000, le=2100)
    monthly_cents: int = Field(ge=0, le=1000000000)


@router.post("/contracts/draft", status_code=201)
def draft(
    payload: DraftIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director", "secretary"})
    template = find(db, m.ServiceRecord, payload.template_id, member)
    if template.module != "contract_templates" or template.status != "published":
        raise HTTPException(422, "Selecione um modelo publicado pela direção.")
    student = find(db, m.Student, payload.student_id, member)
    guardian = find(db, m.Guardian, payload.guardian_id, member)
    if not db.scalar(
        scoped(m.GuardianLink, member).where(
            m.GuardianLink.student_id == student.id,
            m.GuardianLink.guardian_id == guardian.id,
            m.GuardianLink.verified.is_(True),
        )
    ):
        raise HTTPException(
            422, "Selecione um responsável com vínculo verificado ao aluno."
        )
    if not db.scalar(
        scoped(m.AcademicYear, member).where(
            m.AcademicYear.year == payload.academic_year
        )
    ):
        raise HTTPException(422, "Configure o ano letivo antes de preparar a minuta.")
    school = db.get(m.School, member.school_id)
    amount = (
        format(Decimal(payload.monthly_cents) / 100, ",.2f")
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    values = {
        "aluno": student.name,
        "responsavel": guardian.name,
        "escola": school.name,
        "ano_letivo": str(payload.academic_year),
        "mensalidade": "R$ " + amount,
    }
    clauses = template.data["clauses"]
    if set(re.findall(r"\{\{\s*([^{}]+?)\s*\}\}", clauses)) - set(values):
        raise HTTPException(
            422,
            "O modelo contém campos não suportados. Use aluno, responsavel, escola, ano_letivo e mensalidade.",
        )
    text = re.sub(
        r"\{\{\s*([^{}]+?)\s*\}\}",
        lambda match: values[match.group(1).strip()],
        clauses,
    )
    text = (
        f"MINUTA SEM ASSINATURA. Modelo: {template.title}.\nAluno: {student.name}. Responsável: {guardian.name}. Ano letivo: {payload.academic_year}.\n\n"
        + text
    )
    return save_document(
        db,
        member,
        student,
        "contract",
        "Minuta de contrato escolar · " + str(payload.academic_year),
        text,
        [],
    )

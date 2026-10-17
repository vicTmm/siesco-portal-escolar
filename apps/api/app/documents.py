"""Private PDF issuance with public, minimal authenticity metadata."""

import base64
import hashlib
import io
import os
import re
from datetime import datetime, timezone
from secrets import token_urlsafe
from typing import Literal
from uuid import UUID
from xml.sax.saxutils import escape
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)
from sqlalchemy import select
from sqlalchemy.orm import Session
from .pdf_styles import FONT, BOLD, styles as school_styles, validate_text
from . import models as m
from .schemas import Schema
from .db import database, tenant_context
from .domain import scoped, find, audit
from .security import membership, permit, MANAGERS, hash_token
from .community import student_ids
from .learning import family_access, report
from .annual import report as annual_report

router = APIRouter(prefix="/api/v1", tags=["Documentos escolares"])
TITLES = {
    "enrollment": "Declaração de matrícula",
    "attendance": "Declaração de frequência",
    "report": "Boletim escolar",
    "history": "Histórico de resultados publicados",
}


class IssueIn(Schema):
    student_id: UUID
    kind: Literal["enrollment", "attendance", "report", "history"]
    academic_year: int = Field(ge=2000, le=2100)
    term_id: UUID | None = None


class RevokeIn(Schema):
    reason: str = Field(min_length=10, max_length=1000)


def render_pdf(school, student, title, text, rows, url, issued, charts=None):
    output = io.BytesIO()
    validate_text(
        school, student, title, text, url, *[cell for row in rows for cell in row]
    )
    styles = school_styles()
    styles.add(
        ParagraphStyle(
            name="SchoolHeading",
            fontName=BOLD,
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#17664e"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SchoolBody",
            fontName=FONT,
            fontSize=10,
            leading=16,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SchoolSmall",
            fontName=FONT,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#607268"),
        )
    )

    def p(value, style="SchoolBody"):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

    story = [
        p("SIESCO", "SchoolHeading"),
        p(school, "Heading2"),
        Spacer(1, 8 * mm),
        p(title, "SchoolHeading"),
        p(student, "Heading2"),
        p(text),
        Spacer(1, 5 * mm),
    ]
    if rows:
        table = Table(
            [[p(cell, "SchoolSmall") for cell in row] for row in rows],
            colWidths=[62 * mm, 40 * mm, 30 * mm, 32 * mm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf5ee")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce7df")),
                ]
            )
        )
        story.extend([table, Spacer(1, 4 * mm)])
    if charts:
        story.append(p("Comparativo de desempenho", "Heading3"))
        for point in charts:
            story.append(p(point["label"], "SchoolSmall"))
            chart = Drawing(164 * mm, 22 * mm)
            chart.add(String(0, 12 * mm, "Aluno", fontName=FONT, fontSize=8))
            chart.add(
                Rect(
                    20 * mm,
                    10 * mm,
                    120 * mm * float(point["average"]) / float(point["scale"]),
                    5 * mm,
                    fillColor=colors.HexColor("#17664e"),
                    strokeColor=None,
                )
            )
            chart.add(
                String(
                    142 * mm,
                    12 * mm,
                    str(point["average"]).replace(".", ",")
                    + " / "
                    + str(point["scale"]).replace(".", ","),
                    fontName=FONT,
                    fontSize=7,
                )
            )
            chart.add(String(0, 2 * mm, "Turma", fontName=FONT, fontSize=8))
            if point["class_average"] is not None:
                chart.add(
                    Rect(
                        20 * mm,
                        0,
                        120
                        * mm
                        * float(point["class_average"])
                        / float(point["scale"]),
                        5 * mm,
                        fillColor=colors.HexColor("#90afa1"),
                        strokeColor=None,
                    )
                )
                chart.add(
                    String(
                        142 * mm,
                        2 * mm,
                        str(point["class_average"]).replace(".", ","),
                        fontName=FONT,
                        fontSize=7,
                    )
                )
            else:
                chart.add(
                    String(
                        20 * mm,
                        2 * mm,
                        "Comparativo indisponível",
                        fontName=FONT,
                        fontSize=8,
                        fillColor=colors.HexColor("#607268"),
                    )
                )
            story.extend([chart, Spacer(1, 3 * mm)])
    qr_buffer = io.BytesIO()
    qrcode.make(url).save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    story.append(
        KeepTogether(
            [
                p("Verificação de autenticidade", "Heading3"),
                p(
                    "Escaneie o QR Code ou abra o endereço abaixo. A página confirma a validade e permite comparar o hash do PDF, sem expor os dados do aluno.",
                    "SchoolSmall",
                ),
                Image(qr_buffer, width=30 * mm, height=30 * mm),
                p(url, "SchoolSmall"),
                Spacer(1, 4 * mm),
                p(
                    f"Emitido em {issued.strftime('%d/%m/%Y %H:%M UTC')}. Documento eletrônico registrado pela instituição. Não contém assinatura digital de um prestador externo.",
                    "SchoolSmall",
                ),
            ]
        )
    )

    def footer(canvas, doc):
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.HexColor("#607268"))
        canvas.drawString(23 * mm, 15 * mm, "SIESCO - Documento escolar")
        canvas.drawRightString(187 * mm, 15 * mm, f"Página {doc.page}")

    SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=23 * mm,
        leftMargin=23 * mm,
        topMargin=22 * mm,
        bottomMargin=25 * mm,
        title=title,
        author=school,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def save_document(db, member, student, kind, title, text, rows, charts=None):
    institution = db.get(m.Institution, member.institution_id)
    token = token_urlsafe(32)
    origin = os.environ.get("PUBLIC_APP_URL", "http://localhost:3100").rstrip("/")
    if not origin.startswith(("https://", "http://localhost:")):
        raise HTTPException(503, "Configure a URL pública do portal com HTTPS.")
    issued = datetime.now(timezone.utc)
    school = db.get(m.School, member.school_id)
    content = render_pdf(
        institution.name + " · " + school.name,
        student.name,
        title,
        text,
        rows,
        origin + "/verificar/" + token,
        issued,
        charts,
    )
    document = m.SchoolDocument(
        student_id=student.id,
        kind=kind,
        title=title,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        token=token,
        issued_at=issued,
        institution_id=member.institution_id,
        school_id=member.school_id,
    )
    db.add(document)
    db.flush()
    db.add(
        m.DocumentLookup(
            token_hash=hash_token(token),
            document_id=document.id,
            institution_id=member.institution_id,
        )
    )
    audit(db, member, "documents.issue", document.id)
    return {
        "id": document.id,
        "title": document.title,
        "issued_at": issued,
        "verification_url": origin + "/verificar/" + token,
    }


@router.post("/institutions/{institution_id}/documents", status_code=201)
def issue(
    payload: IssueIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director", "secretary"})
    student = find(db, m.Student, payload.student_id, member)
    enrollment = db.scalar(
        scoped(m.Enrollment, member).where(
            m.Enrollment.student_id == student.id,
            m.Enrollment.academic_year == payload.academic_year,
        )
    )
    if not enrollment:
        raise HTTPException(422, "Aluno sem matrícula neste ano letivo.")
    current = report(student_id=UUID(student.id), member=member, db=db)["items"]
    current = [
        item
        for item in current
        if find(
            db,
            m.AcademicYear,
            find(
                db,
                m.AcademicTerm,
                find(
                    db,
                    m.Journal,
                    find(db, m.Publication, item["id"], member).journal_id,
                    member,
                ).term_id,
                member,
            ).academic_year_id,
            member,
        ).year
        == payload.academic_year
    ]
    selected_term = None
    if payload.term_id:
        if payload.kind not in {"report", "attendance"}:
            raise HTTPException(
                422,
                "O período é usado apenas no boletim e na declaração de frequência.",
            )
        selected_term = find(db, m.AcademicTerm, payload.term_id, member)
        if (
            find(db, m.AcademicYear, selected_term.academic_year_id, member).year
            != payload.academic_year
        ):
            raise HTTPException(422, "O período pertence a outro ano letivo.")
        current = [
            item
            for item in current
            if find(
                db,
                m.Journal,
                find(db, m.Publication, item["id"], member).journal_id,
                member,
            ).term_id
            == selected_term.id
        ]
    rows = []
    group = find(db, m.ClassGroup, enrollment.class_id, member)
    if payload.kind == "enrollment":
        text = f"Declaramos que {student.name} possui matrícula {'ativa' if enrollment.status == 'active' else 'cancelada'} na turma {group.name}, no ano letivo de {payload.academic_year}."
    elif payload.kind in {"report", "attendance"}:
        if not current:
            raise HTTPException(
                422, "Não há resultados publicados para emitir este documento."
            )
        text = f"Resultados publicados pela instituição no ano letivo de {payload.academic_year}. As informações refletem as revisões indicadas e não incluem rascunhos."
        rows = [["Disciplina / período", "Média / conceito", "Frequência", "Revisão"]]
        rows += [
            [
                item["subject"] + " / " + item["term"],
                item["result"]["concept"]
                or (
                    item["result"]["average"]
                    if item["result"]["average"] is not None
                    else "Pendente"
                ),
                str(item["result"]["attendance"]) + "%",
                str(item["revision"]),
            ]
            for item in current
        ]
        if payload.kind == "attendance":
            rows = [
                ["Disciplina / período", "Aulas registradas", "Frequência", "Revisão"]
            ] + [
                [
                    item["subject"] + " / " + item["term"],
                    str(item["result"]["lessons"]),
                    str(item["result"]["attendance"]) + "%",
                    str(item["revision"]),
                ]
                for item in current
            ]
    else:
        published = [
            item
            for item in annual_report(student_id=UUID(student.id), member=member, db=db)
            if item["year"] == payload.academic_year
        ]
        if not published:
            raise HTTPException(
                422, "Publique a consolidação anual antes de emitir o histórico."
            )
        text = f"Consolidação anual de {payload.academic_year} registrada no sistema. Equivalências e resultados externos não são inferidos por este documento."
        rows = [["Disciplina", "Média / conceito", "Frequência", "Resultado"]]
        rows += [
            [
                r["subject"],
                r["concept"] or r["average"] or "Pendente",
                str(r["attendance"]) + "%",
                r["result"],
            ]
            for item in published
            for r in item["results"]
        ]
    charts = (
        [
            {
                "label": item["subject"] + " · " + item["term"],
                "average": item["result"]["average"],
                "scale": item["policy"]["scale"],
                "class_average": item.get("class_average"),
            }
            for item in current
            if item["result"]["average"] is not None
            and item["policy"]["method"] != "concepts"
        ]
        if payload.kind == "report"
        else None
    )
    title = TITLES[payload.kind] + (
        " · " + selected_term.name[:100] if selected_term else ""
    )
    return save_document(db, member, student, payload.kind, title, text, rows, charts)


@router.get("/institutions/{institution_id}/documents")
def documents(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    stmt = scoped(m.SchoolDocument, member)
    if member.role in {"coordinator", "student", "teacher"}:
        stmt = stmt.where(m.SchoolDocument.kind != "contract")
    if member.role not in MANAGERS:
        permit(member, {"student", "guardian"})
        stmt = stmt.where(m.SchoolDocument.student_id.in_(student_ids(db, member)))
    items = db.scalars(
        stmt.order_by(m.SchoolDocument.issued_at.desc(), m.SchoolDocument.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": d.id,
            "student": find(db, m.Student, d.student_id, member).name,
            "title": d.title,
            "issued_at": d.issued_at,
            "revoked": d.revoked,
            "reason": d.reason,
        }
        for d in items
    ]


@router.get("/institutions/{institution_id}/documents/{item_id}/download")
def download(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    d = find(db, m.SchoolDocument, item_id, member)
    if d.kind == "contract":
        permit(member, {"director", "secretary", "guardian"})
    family_access(db, member, d.student_id)
    audit(db, member, "documents.download", d.id)
    return {
        "filename": d.kind + "-" + d.id[:8] + ".pdf",
        "base64": base64.b64encode(d.content).decode(),
    }


@router.post("/institutions/{institution_id}/documents/{item_id}/revoke")
def revoke(
    item_id: UUID,
    payload: RevokeIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director", "secretary"})
    d = find(db, m.SchoolDocument, item_id, member, lock=True)
    d.revoked = True
    d.reason = payload.reason
    audit(db, member, "documents.revoke", d.id)
    return {
        "message": "Documento revogado. A verificação pública passa a informar a revogação."
    }


@router.get("/verify-document/{token}")
def verify(token: str, db: Session = Depends(database, scope="function")):
    if not re.fullmatch(r"[A-Za-z0-9_-]{40,64}", token):
        raise HTTPException(404, "Documento não encontrado.")
    lookup = db.scalar(
        select(m.DocumentLookup).where(m.DocumentLookup.token_hash == hash_token(token))
    )
    if not lookup:
        raise HTTPException(404, "Documento não encontrado.")
    tenant_context(db, lookup.institution_id)
    d = db.get(m.SchoolDocument, lookup.document_id)
    institution = db.get(m.Institution, lookup.institution_id)
    return {
        "title": d.title,
        "institution": institution.name,
        "issued_at": d.issued_at,
        "valid": not d.revoked,
        **({"signature": "unsigned"} if d.kind == "contract" else {}),
        "sha256": d.sha256,
    }

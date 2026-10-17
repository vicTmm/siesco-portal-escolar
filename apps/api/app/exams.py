"""Frozen school-authored exams, separate teacher answer keys and manual answer checking."""

import base64
import io
from random import SystemRandom
from uuid import UUID
from xml.sax.saxutils import escape
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from PIL import Image as PillowImage, ImageOps
from .pdf_styles import FONT, BOLD, styles as school_styles, validate_text
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find, create, audit
from .security import membership, permit
from .learning import assignment_access

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Provas e gabaritos"]
)
ROLES = {"director", "coordinator", "teacher"}


class ExamIn(Schema):
    title: str = Field(min_length=3, max_length=160)
    instructions: str = Field(min_length=3, max_length=2000)
    assignment_id: UUID | None = None
    question_ids: list[UUID] = Field(min_length=1, max_length=50)
    figures: dict[UUID, UUID] = Field(default_factory=dict, max_length=50)
    randomize: bool = False


class AnswersIn(Schema):
    answers: list[str] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def lengths(self):
        if any(len(a) > 4000 for a in self.answers):
            raise ValueError("Respostas devem ter até 4000 caracteres.")
        return self


def access(db, member, identifier):
    permit(member, ROLES)
    r = find(db, m.ServiceRecord, identifier, member)
    if r.module != "exam" or (
        member.role == "teacher" and r.owner_id != member.user_id
    ):
        raise HTTPException(404, "Prova não encontrada.")
    return r


@router.get("/exams")
def exams(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, ROLES)
    stmt = scoped(m.ServiceRecord, member).where(m.ServiceRecord.module == "exam")
    if member.role == "teacher":
        stmt = stmt.where(m.ServiceRecord.owner_id == member.user_id)
    return [
        {
            "id": r.id,
            "title": r.title,
            "class": r.data["class"],
            "question_count": len(r.data["questions"]),
            "created_at": r.created_at,
        }
        for r in db.scalars(
            stmt.order_by(m.ServiceRecord.created_at.desc(), m.ServiceRecord.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/exams", status_code=201)
def assemble(
    payload: ExamIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, ROLES)
    if len(set(payload.question_ids)) != len(payload.question_ids) or set(
        payload.figures
    ) - set(payload.question_ids):
        raise HTTPException(
            422, "Informe questões distintas e figuras das questões selecionadas."
        )
    label = "Prova sem turma definida"
    class_id = None
    if payload.assignment_id:
        a = assignment_access(db, member, payload.assignment_id)
        group = find(db, m.ClassGroup, a.class_id, member)
        class_id = group.id
        label = group.name + " · " + find(db, m.Subject, a.subject_id, member).name
    questions = []
    bytes_total = 0
    for identifier in payload.question_ids:
        q = find(db, m.ServiceRecord, identifier, member)
        if (
            q.module != "questions"
            or q.status != "ready"
            or (member.role == "teacher" and q.owner_id != member.user_id)
        ):
            raise HTTPException(
                422, "Selecione questões prontas e autorizadas para seu perfil."
            )
        figure = payload.figures.get(identifier)
        if figure:
            image = find(db, m.PrivateAttachment, figure, member)
            if image.record_id != q.id or image.mime_type not in {
                "image/png",
                "image/jpeg",
            }:
                raise HTTPException(
                    422, "A figura deve ser uma imagem anexada à questão."
                )
            bytes_total += len(image.content)
        questions.append(
            {
                "id": q.id,
                "title": q.title,
                **q.data,
                "figure_id": str(figure) if figure else None,
            }
        )
    if bytes_total > 8 * 1024 * 1024:
        raise HTTPException(
            422,
            "As figuras desta prova excedem 8 MB. Reduza as imagens ou divida a prova.",
        )
    if payload.randomize:
        SystemRandom().shuffle(questions)
    r = create(
        db,
        m.ServiceRecord,
        {
            "module": "exam",
            "title": payload.title,
            "class_id": class_id,
            "owner_id": member.user_id,
            "data": {
                "class": label,
                "instructions": payload.instructions,
                "questions": questions,
            },
            "status": "frozen",
        },
        member,
    )
    return {"id": r.id, "title": r.title, **r.data}


@router.get("/exams/{item_id}")
def detail(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    r = access(db, member, item_id)
    return {"id": r.id, "title": r.title, **r.data}


def render_exam(school, title, data, figures, answer_key=False):
    output = io.BytesIO()
    validate_text(
        school,
        title,
        data["class"],
        data["instructions"],
        *[
            q[field]
            for q in data["questions"]
            for field in (
                ["title", "answer", "explanation"]
                if answer_key
                else ["prompt", "options"]
            )
        ],
    )
    styles = school_styles()
    styles.add(
        ParagraphStyle(
            name="ExamBody",
            fontName=FONT,
            fontSize=10,
            leading=15,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExamHeading",
            fontName=BOLD,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#17664e"),
            spaceAfter=14,
        )
    )

    def paragraph(text, style="ExamBody"):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])

    story = [
        paragraph(school, "Heading2"),
        paragraph(("Gabarito docente · " if answer_key else "") + title, "ExamHeading"),
        paragraph(data["class"]),
    ]
    if not answer_key:
        story.extend(
            [
                paragraph("Nome: ____________________________________________________"),
                paragraph("Data: ____ / ____ / ______"),
                paragraph(data["instructions"]),
            ]
        )
    for number, q in enumerate(data["questions"], 1):
        heading = f"Questão {number}" + (f" · {q['title']}" if answer_key else "")
        story.append(paragraph(heading, "Heading3"))
        if answer_key:
            story.extend(
                [
                    paragraph("Resposta: " + q["answer"]),
                    paragraph("Justificativa: " + q["explanation"]),
                ]
            )
            continue
        story.append(paragraph(q["prompt"]))
        if q["figure_id"]:
            buffer = io.BytesIO(figures[q["figure_id"]])
            img = Image(buffer)
            factor = min(160 * mm / img.imageWidth, 140 * mm / img.imageHeight)
            img.drawWidth = img.imageWidth * factor
            img.drawHeight = img.imageHeight * factor
            story.extend([img, Spacer(1, 4 * mm)])
        story.extend([paragraph(q["options"]), Spacer(1, 5 * mm)])

    def footer(canvas, doc):
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.HexColor("#607268"))
        canvas.drawString(
            20 * mm,
            13 * mm,
            "SIESCO · "
            + ("Gabarito de uso docente" if answer_key else "Avaliação escolar"),
        )
        canvas.drawRightString(190 * mm, 13 * mm, f"Página {doc.page}")

    SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=title,
        author=school,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


@router.get("/exams/{item_id}/pdf")
def download(
    item_id: UUID,
    answer_key: bool = False,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    r = access(db, member, item_id)
    school = db.get(m.School, member.school_id)
    figures = {}
    pixels = 0
    if not answer_key:
        for q in r.data["questions"]:
            if not q["figure_id"]:
                continue
            attachment = find(db, m.PrivateAttachment, q["figure_id"], member)
            try:
                with PillowImage.open(io.BytesIO(attachment.content)) as original:
                    pixels += original.width * original.height
                    if pixels > 20000000:
                        raise HTTPException(
                            422,
                            "Reduza a resolução das figuras antes de preparar o PDF.",
                        )
                    image = ImageOps.exif_transpose(original).convert("RGB")
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=90)
                    figures[attachment.id] = buffer.getvalue()
            except (OSError, ValueError, PillowImage.DecompressionBombError):
                raise HTTPException(
                    422, "Não foi possível abrir uma das figuras desta prova."
                )
    content = render_exam(school.name, r.title, r.data, figures, answer_key)
    audit(db, member, "exams.answer_key" if answer_key else "exams.pdf", r.id)
    return {
        "filename": ("gabarito-" if answer_key else "prova-") + r.id[:8] + ".pdf",
        "base64": base64.b64encode(content).decode(),
    }


@router.post("/exams/{item_id}/correct")
def correct(
    item_id: UUID,
    payload: AnswersIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    r = access(db, member, item_id)
    if len(payload.answers) != len(r.data["questions"]):
        raise HTTPException(422, "Informe uma resposta por questão da prova.")
    rows = [
        {
            "number": n + 1,
            "correct": answer.strip().casefold() == q["answer"].strip().casefold(),
            "expected": q["answer"],
            "explanation": q["explanation"],
        }
        for n, (q, answer) in enumerate(zip(r.data["questions"], payload.answers))
    ]
    return {
        "correct": sum(row["correct"] for row in rows),
        "total": len(rows),
        "items": rows,
    }

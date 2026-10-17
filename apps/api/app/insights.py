"""Explainable academic alerts, manual answer sheets and bounded timetable search."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find, create
from .security import membership, permit, MANAGERS
from .learning import results
from .services import data_for

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Apoio pedagógico"]
)


@router.get("/alerts")
def alerts(
    academic_year: int = Query(..., ge=2000, le=2100),
    consecutive: int = Query(3, ge=2, le=30),
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS)
    output = []
    for journal in db.scalars(scoped(m.Journal, member)):
        term = find(db, m.AcademicTerm, journal.term_id, member)
        year = find(db, m.AcademicYear, term.academic_year_id, member)
        if year.year != academic_year:
            continue
        policy = find(db, m.GradingPolicy, journal.policy_id, member)
        assignment = find(db, m.Assignment, journal.assignment_id, member)
        subject = find(db, m.Subject, assignment.subject_id, member)
        lessons = list(
            db.scalars(
                scoped(m.Lesson, member)
                .where(m.Lesson.journal_id == journal.id, m.Lesson.cancelled.is_(False))
                .order_by(m.Lesson.date, m.Lesson.id)
            )
        )
        attendance = {
            (a.student_id, a.lesson_id): a.status
            for a in db.scalars(
                scoped(m.Attendance, member).where(
                    m.Attendance.lesson_id.in_([l.id for l in lessons])
                )
            )
        }
        for row in results(db, member, journal):
            reasons = []
            if row["average"] is not None and float(row["average"]) < float(
                policy.passing
            ):
                reasons.append("Média abaixo do mínimo configurado")
            if row["attendance"] is not None and float(row["attendance"]) < float(
                policy.attendance_min
            ):
                reasons.append("Frequência abaixo do mínimo configurado")
            streak = 0
            for lesson in reversed(lessons):
                if attendance.get((row["student_id"], lesson.id)) != "absent":
                    break
                streak += 1
            if streak >= consecutive:
                reasons.append(f"{streak} aulas consecutivas com falta registrada")
            if reasons:
                output.append(
                    {
                        "student_id": row["student_id"],
                        "student": row["name"],
                        "subject": subject.name,
                        "term": term.name,
                        "reasons": reasons,
                        "average": row["average"],
                        "attendance": row["attendance"],
                    }
                )
    return output


class CorrectionIn(Schema):
    question_ids: list[UUID] = Field(min_length=1, max_length=100)
    answers: list[str] = Field(min_length=1, max_length=100)


@router.post("/answer-sheets/correct")
def correct(
    payload: CorrectionIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS | {"teacher"})
    if len(payload.question_ids) != len(payload.answers) or len(
        set(payload.question_ids)
    ) != len(payload.question_ids):
        raise HTTPException(422, "Informe uma resposta por questão distinta.")
    rows = []
    for qid, answer in zip(payload.question_ids, payload.answers):
        q = find(db, m.ServiceRecord, qid, member)
        if q.module != "questions" or q.status != "ready":
            raise HTTPException(422, "Selecione apenas questões prontas para uso.")
        if member.role == "teacher" and q.owner_id != member.user_id:
            raise HTTPException(403, "Questão restrita ao autor.")
        data = data_for(q)
        expected = data["answer"].strip().casefold()
        rows.append(
            {
                "question_id": q.id,
                "title": q.title,
                "correct": answer.strip().casefold() == expected,
                "expected": data["answer"],
                "explanation": data["explanation"],
            }
        )
    return {
        "correct": sum(r["correct"] for r in rows),
        "total": len(rows),
        "items": rows,
    }


class Demand(Schema):
    assignment_id: UUID
    room: str = Field(min_length=1, max_length=60)
    periods: int = Field(ge=1, le=30)
    blocked: list[int] = Field(default_factory=list, max_length=30)


class TimetableIn(Schema):
    title: str = Field(min_length=3, max_length=160)
    academic_year: int = Field(ge=2000, le=2100)
    periods_per_day: int = Field(ge=1, le=10)
    demands: list[Demand] = Field(min_length=1, max_length=100)


@router.post("/timetables", status_code=201)
def timetable(
    payload: TimetableIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director", "coordinator"})
    if len({d.assignment_id for d in payload.demands}) != len(payload.demands):
        raise HTTPException(422, "Informe cada atribuição uma única vez.")
    total = 5 * payload.periods_per_day
    jobs = []
    blocked = {}
    names = {}
    shifts = set()
    for d in payload.demands:
        a = find(db, m.Assignment, d.assignment_id, member)
        group = find(db, m.ClassGroup, a.class_id, member)
        shifts.add(group.shift)
        if len(shifts) > 1:
            raise HTTPException(
                422, "Gere uma proposta por turno para manter horários comparáveis."
            )
        if group.academic_year != payload.academic_year:
            raise HTTPException(422, "Atribuição de outro ano letivo.")
        if any(s < 0 or s >= total for s in d.blocked):
            raise HTTPException(422, "Horário indisponível fora da grade.")
        blocked.setdefault(a.teacher_id, set()).update(d.blocked)
        names[a.id] = {
            "class": group.name,
            "teacher": find(db, m.Teacher, a.teacher_id, member).name,
            "subject": find(db, m.Subject, a.subject_id, member).name,
            "room": d.room,
        }
        jobs.extend(
            [(a.id, a.class_id, a.teacher_id, d.room.strip().casefold())] * d.periods
        )
    if len(jobs) > 150:
        raise HTTPException(422, "Use até 150 aulas nesta geração.")
    jobs.sort(key=lambda j: len(blocked[j[2]]), reverse=True)
    occupied = set()
    solution = []
    attempts = 0
    last = {}

    def solve(index):
        nonlocal attempts
        attempts += 1
        if attempts > 100000:
            return False
        if index == len(jobs):
            return True
        assignment, group, teacher, room = jobs[index]
        previous = last.get(assignment, -1)
        for slot in range(previous + 1, total):
            keys = [
                ("class", group, slot),
                ("teacher", teacher, slot),
                ("room", room, slot),
            ]
            if slot in blocked[teacher] or any(k in occupied for k in keys):
                continue
            occupied.update(keys)
            last[assignment] = slot
            solution.append(
                {
                    "assignment_id": assignment,
                    "day": slot // payload.periods_per_day + 1,
                    "period": slot % payload.periods_per_day + 1,
                    **names[assignment],
                }
            )
            if solve(index + 1):
                return True
            solution.pop()
            occupied.difference_update(keys)
            last[assignment] = previous
        return False

    if not solve(0):
        raise HTTPException(
            409,
            "Não foi encontrada uma grade neste limite de busca. Revise carga, salas e indisponibilidades.",
        )
    record = create(
        db,
        m.ServiceRecord,
        {
            "module": "timetable",
            "title": payload.title,
            "owner_id": member.user_id,
            "status": "draft",
            "data": {
                "academic_year": payload.academic_year,
                "rows": solution,
                "periods_per_day": payload.periods_per_day,
            },
        },
        member,
    )
    return {"id": record.id, "title": record.title, **record.data}


@router.get("/timetables")
def timetables(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, MANAGERS)
    return [
        {"id": r.id, "title": r.title, **r.data}
        for r in db.scalars(
            scoped(m.ServiceRecord, member)
            .where(m.ServiceRecord.module == "timetable")
            .order_by(m.ServiceRecord.created_at.desc(), m.ServiceRecord.id)
            .offset(offset)
            .limit(limit)
        )
    ]

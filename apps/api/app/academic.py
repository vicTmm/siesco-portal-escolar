"""Academic calendar and immutable published curriculum versions."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models as m, schemas as s
from .db import database
from .domain import audit, create, find, scoped
from .security import ACADEMIC_WRITERS, MANAGERS, membership, permit

router = APIRouter(prefix="/api/v1/institutions/{institution_id}", tags=["Organização acadêmica"])


def validate_class_curriculum(db, member, payload, existing=None):
    year = db.scalar(scoped(m.AcademicYear, member).where(m.AcademicYear.year == payload.academic_year))
    if not year:
        raise HTTPException(422, "Cadastre o ano letivo e seu calendário antes de criar a turma.")
    if existing and existing.curriculum_id and str(payload.curriculum_id or "") != existing.curriculum_id:
        raise HTTPException(409, "O currículo vinculado à turma não pode ser substituído; preserve o histórico.")
    if not payload.curriculum_id:
        return
    curriculum = find(db, m.Curriculum, payload.curriculum_id, member, lock=True)
    if curriculum.status != "published":
        raise HTTPException(422, "Publique o currículo antes de vinculá-lo à turma.")
    if curriculum.grade_level != payload.grade_level:
        raise HTTPException(422, "A etapa da turma deve corresponder à etapa do currículo.")
    if existing:
        included = select(m.CurriculumSubject.subject_id).where(m.CurriculumSubject.curriculum_id == curriculum.id)
        incompatible = db.scalar(scoped(m.Assignment, member).where(
            m.Assignment.class_id == existing.id, m.Assignment.subject_id.not_in(included)))
        if incompatible:
            raise HTTPException(409, "Há atribuições de disciplinas que não pertencem a este currículo.")


def calendar_values(payload):
    values = payload.model_dump()
    return {key: str(value) if isinstance(value, UUID) else value for key, value in values.items()}


def validate_year(db, member, payload, existing=None):
    if not existing:
        return
    if payload.year != existing.year:
        raise HTTPException(409, "O número do ano letivo não pode ser alterado; cadastre outro ano.")
    outside = db.scalar(scoped(m.AcademicTerm, member).where(m.AcademicTerm.academic_year_id == existing.id,
        (m.AcademicTerm.start_date < payload.start_date) | (m.AcademicTerm.end_date > payload.end_date)))
    if outside:
        raise HTTPException(409, "O calendário não pode deixar períodos cadastrados fora de suas datas.")


def validate_term(db, member, payload, existing=None):
    if existing and str(payload.academic_year_id) != existing.academic_year_id:
        raise HTTPException(409, "O período não pode ser movido para outro ano letivo.")
    year = find(db, m.AcademicYear, payload.academic_year_id, member, lock=True)
    if payload.start_date < year.start_date or payload.end_date > year.end_date:
        raise HTTPException(422, "As datas do período devem estar dentro do calendário do ano letivo.")
    # Parent row lock serializes concurrent period changes in this calendar.
    conflict = db.scalar(scoped(m.AcademicTerm, member).where(
        m.AcademicTerm.academic_year_id == year.id, m.AcademicTerm.id != (existing.id if existing else ""),
        m.AcademicTerm.start_date <= payload.end_date, m.AcademicTerm.end_date >= payload.start_date))
    if conflict:
        raise HTTPException(409, "As datas deste período se sobrepõem a outro período do ano letivo.")
    wrong_order = db.scalar(scoped(m.AcademicTerm, member).where(
        m.AcademicTerm.academic_year_id == year.id, m.AcademicTerm.id != (existing.id if existing else ""),
        ((m.AcademicTerm.sequence < payload.sequence) & (m.AcademicTerm.start_date > payload.start_date)) |
        ((m.AcademicTerm.sequence > payload.sequence) & (m.AcademicTerm.start_date < payload.start_date))))
    if wrong_order:
        raise HTTPException(409, "A sequência dos períodos deve acompanhar a ordem das datas.")


def validate_curriculum(db, member, payload, existing=None):
    if existing and existing.status == "published":
        raise HTTPException(409, "Currículo publicado não pode ser alterado. Cadastre uma nova versão.")
    if existing and (payload.code != existing.code or payload.version != existing.version):
        raise HTTPException(409, "Código e versão identificam o currículo e não podem ser alterados.")


def validate_component(db, member, payload, existing=None):
    if existing and str(payload.curriculum_id) != existing.curriculum_id:
        raise HTTPException(409, "O componente não pode ser movido para outro currículo.")
    curriculum = find(db, m.Curriculum, payload.curriculum_id, member, lock=True)
    if curriculum.status != "draft":
        raise HTTPException(409, "Currículo publicado não pode ser alterado. Cadastre uma nova versão.")
    find(db, m.Subject, payload.subject_id, member)


def register_academic(path, model, schema, output, validate):
    def list_items(member=Depends(membership), db: Session = Depends(database, scope="function"),
                   offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
        permit(member, MANAGERS)
        order = [model.name, model.id] if hasattr(model, "name") else [model.id]
        return db.scalars(scoped(model, member).order_by(*order).offset(offset).limit(limit)).all()

    def create_item(payload: schema, member=Depends(membership), db: Session = Depends(database, scope="function")):
        permit(member, ACADEMIC_WRITERS)
        validate(db, member, payload)
        return create(db, model, calendar_values(payload), member)

    def update_item(item_id: UUID, payload: schema, member=Depends(membership), db: Session = Depends(database, scope="function")):
        permit(member, ACADEMIC_WRITERS)
        # Children lock their parent before their own row, matching publication.
        if model is m.AcademicTerm:
            current = find(db, model, item_id, member)
            find(db, m.AcademicYear, current.academic_year_id, member, lock=True)
        elif model is m.CurriculumSubject:
            current = find(db, model, item_id, member)
            find(db, m.Curriculum, current.curriculum_id, member, lock=True)
        item = find(db, model, item_id, member, lock=True)
        validate(db, member, payload, item)
        for key, value in calendar_values(payload).items():
            setattr(item, key, value)
        if model is m.AcademicYear:
            item.needs_review = False
        audit(db, member, model.__tablename__ + ".update", item.id)
        db.flush()
        return item

    router.add_api_route("/" + path, list_items, methods=["GET"], response_model=list[output], name="list_" + path)
    router.add_api_route("/" + path, create_item, methods=["POST"], response_model=output, status_code=201, name="create_" + path)
    router.add_api_route("/" + path + "/{item_id}", update_item, methods=["PUT"], response_model=output, name="update_" + path)


for args in [("academic-years", m.AcademicYear, s.AcademicYearIn, s.AcademicYearOut, validate_year),
             ("academic-terms", m.AcademicTerm, s.AcademicTermIn, s.AcademicTermOut, validate_term),
             ("curricula", m.Curriculum, s.CurriculumIn, s.CurriculumOut, validate_curriculum),
             ("curriculum-subjects", m.CurriculumSubject, s.CurriculumSubjectIn, s.CurriculumSubjectOut, validate_component)]:
    register_academic(*args)


@router.post("/curricula/{item_id}/publish", response_model=s.CurriculumOut)
def publish_curriculum(item_id: UUID, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, ACADEMIC_WRITERS)
    curriculum = find(db, m.Curriculum, item_id, member, lock=True)
    if curriculum.status == "published":
        return curriculum
    if not db.scalar(scoped(m.CurriculumSubject, member).where(m.CurriculumSubject.curriculum_id == curriculum.id)):
        raise HTTPException(422, "Inclua pelo menos uma disciplina antes de publicar o currículo.")
    curriculum.status = "published"
    audit(db, member, "curricula.publish", curriculum.id)
    db.flush()
    return curriculum


@router.delete("/curriculum-subjects/{item_id}", status_code=204)
def remove_component(item_id: UUID, member=Depends(membership), db: Session = Depends(database, scope="function")):
    permit(member, ACADEMIC_WRITERS)
    item = find(db, m.CurriculumSubject, item_id, member)
    curriculum = find(db, m.Curriculum, item.curriculum_id, member, lock=True)
    if curriculum.status != "draft":
        raise HTTPException(409, "Currículo publicado não pode ser alterado.")
    item = find(db, m.CurriculumSubject, item_id, member, lock=True)
    audit(db, member, "curriculum_subjects.delete", item.id)
    db.delete(item)

"""Enrollment movements preserve effective date intervals and their reasons."""
from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from . import models as m
from .learning_schemas import MoveIn
from .db import database
from .domain import scoped,find,create,audit
from .security import membership,permit,MANAGERS,PEOPLE_WRITERS

router=APIRouter(prefix='/api/v1/institutions/{institution_id}',tags=['Movimentação de matrículas'])


@router.get('/enrollments/{item_id}/history')
def history(item_id:UUID,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,MANAGERS);find(db,m.Enrollment,item_id,member)
    return {'placements':[{'id':p.id,'class_id':p.class_id,'start_date':p.start_date,'end_date':p.end_date} for p in db.scalars(scoped(m.Placement,member).where(m.Placement.enrollment_id==str(item_id)).order_by(m.Placement.start_date))],
            'movements':[{'id':x.id,'action':x.action,'reason':x.reason,'date':x.date,'class_id':x.class_id} for x in db.scalars(scoped(m.EnrollmentMovement,member).where(m.EnrollmentMovement.enrollment_id==str(item_id)).order_by(m.EnrollmentMovement.date,m.EnrollmentMovement.id))]}


@router.post('/enrollments/{item_id}/move')
def move(item_id:UUID,payload:MoveIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,PEOPLE_WRITERS)
    # All enrollment operations lock classes in ID order before enrollment.
    original=find(db,m.Enrollment,item_id,member)
    original_class=original.class_id
    target=str(payload.class_id) if payload.class_id else original.class_id
    for class_id in sorted({original.class_id,target}):find(db,m.ClassGroup,class_id,member,lock=True)
    e=find(db,m.Enrollment,item_id,member,lock=True)
    if e.class_id!=original_class:raise HTTPException(409,'Matrícula alterada. Atualize a tela.')
    group=find(db,m.ClassGroup,target,member)
    year=db.scalar(scoped(m.AcademicYear,member).where(m.AcademicYear.year==e.academic_year))
    if group.academic_year!=e.academic_year or not year.start_date<=payload.date<=year.end_date:raise HTTPException(422,'Movimentação deve permanecer no ano letivo e em suas datas.')
    if payload.action in {'transfer','cancel'} and e.status!='active':raise HTTPException(409,'Matrícula não está ativa.')
    if payload.action=='reactivate' and e.status!='cancelled':raise HTTPException(409,'Matrícula já está ativa.')
    if payload.action=='transfer' and target==e.class_id:raise HTTPException(422,'Selecione uma turma diferente.')
    # Avoid retroactive reassignment of already recorded academic data.
    assignment_ids=select(m.Assignment.id).where(m.Assignment.class_id.in_([e.class_id,target]))
    journal_ids=select(m.Journal.id).where(m.Journal.assignment_id.in_(assignment_ids))
    if db.scalar(scoped(m.Lesson,member).where(m.Lesson.journal_id.in_(journal_ids),m.Lesson.date>=payload.date)) or db.scalar(scoped(m.Assessment,member).where(m.Assessment.journal_id.in_(journal_ids),m.Assessment.date>=payload.date)):
        raise HTTPException(409,'Há registros acadêmicos a partir desta data. Concilie os diários antes de movimentar.')
    placements=db.scalars(scoped(m.Placement,member).where(m.Placement.enrollment_id==e.id).order_by(m.Placement.start_date)).all()
    opened=next((p for p in placements if p.end_date is None),None)
    if payload.action!='reactivate':
        if not opened or payload.date<=opened.start_date:raise HTTPException(422,'A movimentação deve ser posterior ao início da alocação atual.')
        opened.end_date=payload.date;db.flush()
    elif placements and (placements[-1].end_date is None or payload.date<placements[-1].end_date):raise HTTPException(422,'Reativação não pode sobrepor o histórico.')
    if payload.action!='cancel':
        count=db.scalar(select(func.count()).select_from(m.Enrollment).where(m.Enrollment.class_id==target,m.Enrollment.status=='active',m.Enrollment.id!=e.id))
        if count>=group.capacity:raise HTTPException(409,'A turma está sem vagas.')
        create(db,m.Placement,{'enrollment_id':e.id,'class_id':target,'start_date':payload.date},member)
        e.class_id=target;e.status='active'
    else:e.status='cancelled'
    create(db,m.EnrollmentMovement,{'enrollment_id':e.id,'class_id':target,'action':payload.action,'date':payload.date,'reason':payload.reason},member)
    audit(db,member,'enrollments.'+payload.action,e.id);db.flush()
    return {'id':e.id,'class_id':e.class_id,'status':e.status}

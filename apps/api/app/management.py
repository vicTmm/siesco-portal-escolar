"""Search, audit access and authorized tabular exports."""
import csv
import io
from fastapi import APIRouter,Depends,Query,HTTPException
from sqlalchemy import select,or_
from sqlalchemy.orm import Session
from . import models as m
from .db import database
from .domain import scoped,audit
from .security import membership,permit,MANAGERS

router=APIRouter(prefix='/api/v1/institutions/{institution_id}',tags=['Busca e auditoria'])


@router.get('/search')
def search(q:str=Query('',min_length=2,max_length=100),member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,MANAGERS);result=[]
    for resource,model in [('students',m.Student),('guardians',m.Guardian),('teachers',m.Teacher),('classes',m.ClassGroup),('subjects',m.Subject)]:
        for x in db.scalars(scoped(model,member).where(model.name.icontains(q,autoescape=True)).order_by(model.name,model.id).limit(20)):
            result.append({'id':x.id,'name':x.name,'resource':resource})
    return result


@router.get('/audit')
def events(member=Depends(membership),db:Session=Depends(database,scope='function'),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),q:str=Query('',max_length=100)):
    permit(member,{'director'})
    stmt=scoped(m.AuditEvent,member)
    if q:stmt=stmt.where(m.AuditEvent.action.icontains(q,autoescape=True))
    rows=db.scalars(stmt.order_by(m.AuditEvent.occurred_at.desc(),m.AuditEvent.id).offset(offset).limit(limit)).all()
    return [{'id':x.id,'action':x.action,'entity_id':x.entity_id,'actor_id':x.actor_id,'occurred_at':x.occurred_at} for x in rows]


def csv_cell(value):
    value=str(value or '')
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value


@router.get('/exports/{resource}')
def export(resource:str,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,{'director','secretary'})
    if resource not in {'students','enrollments','classes'}:raise HTTPException(404,'Relatório não encontrado.')
    out=io.StringIO();writer=csv.writer(out,delimiter=';')
    if resource=='students':
        writer.writerow(['Aluno','Nascimento'])
        for s in db.scalars(scoped(m.Student,member).order_by(m.Student.name,m.Student.id)):
            writer.writerow([csv_cell(s.name),s.birth_date.isoformat()])
    elif resource=='classes':
        writer.writerow(['Turma','Ano','Turno','Capacidade'])
        for c in db.scalars(scoped(m.ClassGroup,member).order_by(m.ClassGroup.name,m.ClassGroup.id)):
            writer.writerow([csv_cell(c.name),c.academic_year,c.shift,c.capacity])
    else:
        writer.writerow(['Aluno','Turma','Ano','Situação'])
        for e,s,c in db.execute(select(m.Enrollment,m.Student,m.ClassGroup).join(m.Student,m.Student.id==m.Enrollment.student_id).join(m.ClassGroup,m.ClassGroup.id==m.Enrollment.class_id).where(m.Enrollment.institution_id==member.institution_id,m.Enrollment.school_id==member.school_id).order_by(m.Student.name,m.Enrollment.id)):
            writer.writerow([csv_cell(s.name),csv_cell(c.name),e.academic_year,e.status])
    audit(db,member,'exports.'+resource,member.school_id)
    # JSON through BFF, then user-triggered download. No public artifact is stored.
    return {'filename':resource+'.csv','content':'\ufeff'+out.getvalue()}

"""Annual consolidation from published period snapshots, with explicit weights."""
from decimal import Decimal,ROUND_HALF_UP
from uuid import UUID
from pydantic import Field,model_validator
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped,find,create
from .security import membership,permit,ACADEMIC_WRITERS,MANAGERS
from .learning import family_access

router=APIRouter(prefix='/api/v1/institutions/{institution_id}',tags=['Consolidação anual'])


class Weight(Schema):
    term_id:UUID
    weight:Decimal=Field(gt=0,le=1000,decimal_places=2)


class AnnualIn(Schema):
    name:str=Field(min_length=2,max_length=160)
    academic_year_id:UUID
    policy_id:UUID
    weights:list[Weight]=Field(min_length=1,max_length=24)
    @model_validator(mode='after')
    def unique(self):
        if len({w.term_id for w in self.weights})!=len(self.weights):raise ValueError('Período duplicado.')
        return self


class FinalRecovery(Schema):
    subject_id:UUID
    value:Decimal=Field(ge=0,decimal_places=2)


class AnnualPublish(Schema):
    recoveries:list[FinalRecovery]=Field(default_factory=list,max_length=100)


@router.get('/annual-policies')
def policies(member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,MANAGERS)
    return [{'id':p.id,'name':p.name,'academic_year_id':p.academic_year_id,'policy_id':p.policy_id,'weights':p.weights} for p in db.scalars(scoped(m.AnnualPolicy,member).order_by(m.AnnualPolicy.name,m.AnnualPolicy.id))]


@router.post('/annual-policies',status_code=201)
def configure(payload:AnnualIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,ACADEMIC_WRITERS);find(db,m.AcademicYear,payload.academic_year_id,member,lock=True);find(db,m.GradingPolicy,payload.policy_id,member)
    existing=db.scalars(scoped(m.AcademicTerm,member).where(m.AcademicTerm.academic_year_id==str(payload.academic_year_id))).all()
    if {t.id for t in existing}!={str(w.term_id) for w in payload.weights}:raise HTTPException(422,'Inclua todos os períodos cadastrados no ano e somente eles.')
    p=create(db,m.AnnualPolicy,{'name':payload.name,'academic_year_id':str(payload.academic_year_id),'policy_id':str(payload.policy_id),'weights':[{'term_id':str(w.term_id),'weight':str(w.weight)} for w in payload.weights]},member)
    return {'id':p.id}


def consolidate(db,member,annual,student_id,recoveries=None):
    student=find(db,m.Student,student_id,member);year=find(db,m.AcademicYear,annual.academic_year_id,member);policy=find(db,m.GradingPolicy,annual.policy_id,member)
    enrollments=db.scalars(scoped(m.Enrollment,member).where(m.Enrollment.student_id==student.id,m.Enrollment.academic_year==year.year)).all()
    if not enrollments:raise HTTPException(422,'Aluno não possui matrícula neste ano.')
    placements=db.scalars(scoped(m.Placement,member).where(m.Placement.enrollment_id.in_([e.id for e in enrollments]))).all()
    assignments=db.scalars(scoped(m.Assignment,member).where(m.Assignment.class_id.in_([p.class_id for p in placements]))).all()
    subjects={a.subject_id for a in assignments}
    # A published curriculum defines required subjects even if an assignment is missing.
    for group in db.scalars(scoped(m.ClassGroup,member).where(m.ClassGroup.id.in_([p.class_id for p in placements]))):
        if group.curriculum_id:subjects.update(db.scalars(select(m.CurriculumSubject.subject_id).where(m.CurriculumSubject.curriculum_id==group.curriculum_id)))
    publications=db.scalars(scoped(m.Publication,member).order_by(m.Publication.published_at.desc())).all();seen=set();periods={};sources=[]
    for pub in publications:
        if pub.journal_id in seen:continue
        seen.add(pub.journal_id);journal=find(db,m.Journal,pub.journal_id,member);term=find(db,m.AcademicTerm,journal.term_id,member)
        if term.academic_year_id!=year.id:continue
        assignment=find(db,m.Assignment,journal.assignment_id,member)
        row=next((r for r in pub.snapshot['results'] if r['student_id']==student.id),None)
        if row:
            periods.setdefault((assignment.subject_id,term.id),[]).append((row,Decimal(pub.snapshot['policy']['scale'])))
            sources.append(pub.id)
    output=[];rec=recoveries or {}
    for subject in sorted(subjects):
        weighted=Decimal(0);denominator=Decimal(0);lessons=0;absences=0;pending=0;term_rows=[]
        for weight in annual.weights:
            term=find(db,m.AcademicTerm,weight['term_id'],member)
            # Only periods overlapping the student's actual enrollment intervals count.
            relevant=any(p.start_date<=term.end_date and (p.end_date is None or p.end_date>term.start_date) for p in placements)
            if not relevant:continue
            candidates=periods.get((subject,term.id),[])
            if not candidates:pending+=1;term_rows.append({'term':term.name,'average':None});continue
            count=sum(row['lessons'] for row,scale in candidates)
            value=sum(Decimal(row['average'])/scale*policy.scale*row['lessons'] for row,scale in candidates)/count
            w=Decimal(weight['weight']);weighted+=value*w;denominator+=w
            lessons+=count;absences+=sum(row['absences'] for row,scale in candidates)
            term_rows.append({'term':term.name,'average':str(value.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))})
        average=(weighted/denominator).quantize(Decimal(1).scaleb(-policy.decimals),rounding=ROUND_HALF_UP) if denominator and not pending else None
        frequency=(Decimal(lessons-absences)*100/lessons).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if lessons else None
        if average is not None and average<policy.passing and policy.recovery!='none':
            if subject not in rec:pending+=1
            else:
                r=rec[subject]
                average=(max(average,r) if policy.recovery=='best' else r if policy.recovery=='replace' else (average+r)/2).quantize(Decimal(1).scaleb(-policy.decimals),rounding=ROUND_HALF_UP)
        label=None
        if average is not None and policy.method=='concepts':label=next((c['label'] for c in sorted(policy.concepts,key=lambda c:Decimal(c['minimum']),reverse=True) if average/policy.scale*100>=Decimal(c['minimum'])),None)
        output.append({'subject_id':subject,'subject':find(db,m.Subject,subject,member).name,'average':str(average) if average is not None else None,'concept':label,'attendance':str(frequency) if frequency is not None else None,'pending':pending,'periods':term_rows,'recovery':str(rec[subject]) if subject in rec else None,'result':'Pendente' if pending or average is None or frequency is None else 'Aprovado' if average>=policy.passing and frequency>=policy.attendance_min else 'Abaixo dos critérios anuais'})
    return {'student':student.name,'year':year.year,'name':annual.name,'policy':{'name':policy.name,'scale':str(policy.scale),'passing':str(policy.passing),'attendance_min':str(policy.attendance_min),'recovery':policy.recovery,'decimals':policy.decimals},'sources':sources,'results':output}


@router.get('/annual-policies/{item_id}/students/{student_id}')
def preview(item_id:UUID,student_id:UUID,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,MANAGERS);annual=find(db,m.AnnualPolicy,item_id,member)
    return consolidate(db,member,annual,student_id)


@router.post('/annual-policies/{item_id}/students/{student_id}/publish')
def publish(item_id:UUID,student_id:UUID,payload:AnnualPublish,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,ACADEMIC_WRITERS);annual=find(db,m.AnnualPolicy,item_id,member);find(db,m.AcademicYear,annual.academic_year_id,member,lock=True);policy=find(db,m.GradingPolicy,annual.policy_id,member)
    # Lock journals in stable order to serialize publication/reopening with finalization.
    db.scalars(scoped(m.Journal,member).order_by(m.Journal.id).with_for_update()).all()
    recovery={str(r.subject_id):r.value for r in payload.recoveries}
    if len(recovery)!=len(payload.recoveries) or any(r.value>policy.scale for r in payload.recoveries):raise HTTPException(422,'Recuperação duplicada ou fora da escala.')
    snapshot=consolidate(db,member,annual,student_id,recovery)
    if set(recovery)-{r['subject_id'] for r in snapshot['results']}:raise HTTPException(422,'Recuperação de disciplina não cursada.')
    if not snapshot['results'] or any(r['pending'] or r['average'] is None for r in snapshot['results']):raise HTTPException(409,'Publique todos os períodos e resolva as recuperações antes de finalizar.')
    version=(db.scalar(select(func.max(m.AnnualPublication.revision)).where(m.AnnualPublication.annual_policy_id==annual.id,m.AnnualPublication.student_id==str(student_id))) or 0)+1
    p=create(db,m.AnnualPublication,{'annual_policy_id':annual.id,'student_id':str(student_id),'revision':version,'snapshot':snapshot},member)
    return {'id':p.id,'revision':version}


@router.get('/annual-reports/{student_id}')
def report(student_id:UUID,member=Depends(membership),db:Session=Depends(database,scope='function')):
    family_access(db,member,student_id)
    items=db.scalars(scoped(m.AnnualPublication,member).where(m.AnnualPublication.student_id==str(student_id)).order_by(m.AnnualPublication.published_at.desc())).all();seen=set();result=[]
    for p in items:
        if p.annual_policy_id in seen:continue
        seen.add(p.annual_policy_id);result.append({'id':p.id,'revision':p.revision,'published_at':p.published_at,**p.snapshot})
    return result

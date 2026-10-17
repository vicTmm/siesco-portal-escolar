"""Scoped school diary, explicit grading policies and immutable report publications."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from . import models as m
from . import learning_schemas as s
from .db import database
from .domain import scoped, find, create, audit
from .security import membership, permit, MANAGERS, ACADEMIC_WRITERS, PEOPLE_WRITERS

router = APIRouter(prefix='/api/v1/institutions/{institution_id}', tags=['Diário e boletins'])


def dto(row, keys):
    return {key: getattr(row, key) for key in ['id', *keys.split()]}


def assignment_access(db, member, identifier):
    permit(member, MANAGERS | {'teacher'})
    assignment = find(db, m.Assignment, identifier, member)
    if member.role == 'teacher' and assignment.teacher_id != member.teacher_id:
        raise HTTPException(404, 'Atribuição não encontrada.')
    return assignment


def journal_access(db, member, identifier, version=None, editable=False):
    journal = find(db, m.Journal, identifier, member, lock=True)
    assignment_access(db, member, journal.assignment_id)
    if editable:
        # Serialize roster changes with enrollment movement/admission for this class.
        assignment=find(db,m.Assignment,journal.assignment_id,member)
        find(db,m.ClassGroup,assignment.class_id,member,lock=True)
        permit(member, ACADEMIC_WRITERS | {'teacher'})
        if journal.status != 'draft':
            raise HTTPException(409, 'Diário fechado. Solicite reabertura à direção.')
    if version is not None and journal.version != version:
        raise HTTPException(409, 'Este diário foi alterado. Atualize a tela antes de salvar.')
    return journal


def changed(db, member, journal, action, identifier):
    journal.version += 1
    audit(db, member, action, identifier)
    db.flush()
    return {'version': journal.version}


def check_date(db, member, journal, value):
    term = find(db, m.AcademicTerm, journal.term_id, member)
    if not term.start_date <= value <= term.end_date:
        raise HTTPException(422, 'Data fora do período letivo.')


def roster(db, member, journal, on=None):
    assignment = find(db, m.Assignment, journal.assignment_id, member)
    term = find(db, m.AcademicTerm, journal.term_id, member)
    start, end = (on, on) if on else (term.start_date, term.end_date)
    return db.scalars(scoped(m.Student, member).where(m.Student.id.in_(
        select(m.Enrollment.student_id).join(m.Placement, m.Placement.enrollment_id == m.Enrollment.id).where(
            m.Placement.class_id == assignment.class_id, m.Placement.start_date <= end,
            (m.Placement.end_date.is_(None)) | (m.Placement.end_date > start)))).order_by(m.Student.name, m.Student.id)).all()


@router.get('/learning/options')
def options(member=Depends(membership), db: Session=Depends(database, scope='function')):
    permit(member, MANAGERS | {'teacher'})
    stmt = scoped(m.Assignment, member)
    if member.role == 'teacher': stmt = stmt.where(m.Assignment.teacher_id == member.teacher_id)
    assignments = db.scalars(stmt.order_by(m.Assignment.id)).all()
    return {'assignments': [{'id': a.id, 'name': find(db,m.ClassGroup,a.class_id,member).name+' · '+find(db,m.Subject,a.subject_id,member).name} for a in assignments],
            'terms': [dto(t,'name academic_year_id') for t in db.scalars(scoped(m.AcademicTerm,member).order_by(m.AcademicTerm.start_date,m.AcademicTerm.id))],
            'policies': [dto(p,'name method scale passing attendance_min decimals recovery concepts') for p in db.scalars(scoped(m.GradingPolicy,member).order_by(m.GradingPolicy.name,m.GradingPolicy.id))]}


@router.post('/grading-policies', status_code=201)
def policy(payload:s.PolicyIn, member=Depends(membership), db: Session=Depends(database, scope='function')):
    permit(member, ACADEMIC_WRITERS)
    item = create(db,m.GradingPolicy,{**payload.model_dump(exclude={'concepts'}), 'concepts':[{'label':c.label,'minimum':str(c.minimum)} for c in payload.concepts]},member)
    return dto(item,'name method scale passing attendance_min decimals recovery concepts')


@router.get('/journals')
def journals(member=Depends(membership), db:Session=Depends(database,scope='function'), offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
    permit(member, MANAGERS | {'teacher'})
    statement=scoped(m.Journal,member)
    if member.role=='teacher': statement=statement.where(m.Journal.assignment_id.in_(select(m.Assignment.id).where(m.Assignment.teacher_id==member.teacher_id)))
    result=[]
    for j in db.scalars(statement.order_by(m.Journal.id).offset(offset).limit(limit)):
        a=find(db,m.Assignment,j.assignment_id,member)
        result.append({**dto(j,'assignment_id term_id policy_id status version'),'name':find(db,m.ClassGroup,a.class_id,member).name+' · '+find(db,m.Subject,a.subject_id,member).name,'term':find(db,m.AcademicTerm,j.term_id,member).name})
    return result


@router.post('/journals',status_code=201)
def new_journal(payload:s.JournalIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,ACADEMIC_WRITERS)
    a=find(db,m.Assignment,payload.assignment_id,member)
    group=find(db,m.ClassGroup,a.class_id,member)
    term=find(db,m.AcademicTerm,payload.term_id,member)
    year=find(db,m.AcademicYear,term.academic_year_id,member)
    if group.academic_year!=year.year: raise HTTPException(422,'Turma e período devem pertencer ao mesmo ano.')
    find(db,m.GradingPolicy,payload.policy_id,member)
    j=create(db,m.Journal,payload.model_dump(mode='json'),member)
    return dto(j,'assignment_id term_id policy_id status version')


@router.get('/journals/{item_id}')
def journal_detail(item_id:UUID,member=Depends(membership),db:Session=Depends(database,scope='function')):
    j=journal_access(db,member,item_id)
    lessons=db.scalars(scoped(m.Lesson,member).where(m.Lesson.journal_id==j.id).order_by(m.Lesson.date,m.Lesson.slot)).all()
    assessments=db.scalars(scoped(m.Assessment,member).where(m.Assessment.journal_id==j.id).order_by(m.Assessment.date,m.Assessment.id)).all()
    return {**dto(j,'assignment_id term_id policy_id status version'), 'students':[dto(x,'name') for x in roster(db,member,j)],
        'policy':dto(find(db,m.GradingPolicy,j.policy_id,member),'name method scale passing attendance_min decimals recovery concepts'),
        'lessons':[{**dto(l,'date slot content cancelled'),'students':[x.id for x in roster(db,member,j,l.date)],'attendance':[dto(a,'student_id status') for a in db.scalars(scoped(m.Attendance,member).where(m.Attendance.lesson_id==l.id))]} for l in lessons],
        'assessments':[{**dto(a,'name date maximum weight kind'),'students':[x.id for x in roster(db,member,j,a.date)],'grades':[dto(g,'student_id value') for g in db.scalars(scoped(m.Grade,member).where(m.Grade.assessment_id==a.id))]} for a in assessments],
        'results': results(db,member,j),
        'publications':[dto(p,'revision published_at') for p in db.scalars(scoped(m.Publication,member).where(m.Publication.journal_id==j.id).order_by(m.Publication.revision.desc()))]}


@router.post('/journals/{item_id}/lessons',status_code=201)
def add_lesson(item_id:UUID,payload:s.LessonIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    j=journal_access(db,member,item_id,payload.version,True); check_date(db,member,j,payload.date)
    l=create(db,m.Lesson,{'journal_id':j.id,**payload.model_dump(exclude={'version'})},member)
    return {**dto(l,'date slot content cancelled'),**changed(db,member,j,'lessons.add',l.id)}


@router.post('/lessons/{item_id}/cancel')
def cancel_lesson(item_id:UUID,payload:s.VersionIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    l=find(db,m.Lesson,item_id,member);j=journal_access(db,member,l.journal_id,payload.version,True)
    l.cancelled=True
    return changed(db,member,j,'lessons.cancel',l.id)


def unique_entries(entries):
    if len({str(x.student_id) for x in entries})!=len(entries): raise HTTPException(422,'Aluno duplicado no lote.')


@router.put('/lessons/{item_id}/attendance')
def attendance(item_id:UUID,payload:s.AttendanceIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    l=find(db,m.Lesson,item_id,member);j=journal_access(db,member,l.journal_id,payload.version,True)
    if l.cancelled: raise HTTPException(409,'Aula cancelada não recebe chamada.')
    unique_entries(payload.entries)
    allowed={x.id for x in roster(db,member,j,l.date)}
    if any(str(e.student_id) not in allowed for e in payload.entries): raise HTTPException(422,'Aluno sem matrícula nesta turma na data da aula.')
    for e in payload.entries:
        record=db.scalar(scoped(m.Attendance,member).where(m.Attendance.lesson_id==l.id,m.Attendance.student_id==str(e.student_id)))
        if record:record.status=e.status
        else:create(db,m.Attendance,{'lesson_id':l.id,**e.model_dump(mode='json')},member)
    return changed(db,member,j,'attendance.save',l.id)


@router.post('/journals/{item_id}/assessments',status_code=201)
def assessment(item_id:UUID,payload:s.AssessmentIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    j=journal_access(db,member,item_id,payload.version,True);check_date(db,member,j,payload.date)
    p=find(db,m.GradingPolicy,j.policy_id,member)
    if payload.kind=='recovery' and p.recovery=='none':raise HTTPException(422,'A regra escolhida não utiliza recuperação.')
    if payload.kind=='recovery' and db.scalar(scoped(m.Assessment,member).where(m.Assessment.journal_id==j.id,m.Assessment.kind=='recovery')):raise HTTPException(409,'Este diário já tem uma avaliação de recuperação.')
    a=create(db,m.Assessment,{'journal_id':j.id,**payload.model_dump(exclude={'version'})},member)
    return {**dto(a,'name date maximum weight kind'),**changed(db,member,j,'assessments.add',a.id)}


@router.put('/assessments/{item_id}/grades')
def grades(item_id:UUID,payload:s.GradesIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    a=find(db,m.Assessment,item_id,member);j=journal_access(db,member,a.journal_id,payload.version,True)
    unique_entries(payload.entries);allowed={x.id for x in roster(db,member,j,a.date)}
    if any(str(e.student_id) not in allowed or (e.value is not None and e.value>a.maximum) for e in payload.entries):raise HTTPException(422,'Aluno não elegível ou nota acima do máximo da avaliação.')
    for e in payload.entries:
        g=db.scalar(scoped(m.Grade,member).where(m.Grade.assessment_id==a.id,m.Grade.student_id==str(e.student_id)))
        if g:g.value=e.value
        else:create(db,m.Grade,{'assessment_id':a.id,'student_id':str(e.student_id),'value':e.value},member)
    return changed(db,member,j,'grades.save',a.id)


def calculate(policy, regular, recovery=None):
    if not regular:return None
    if policy.method=='points':value=sum(v for v,maximum,w in regular)/sum(maximum for v,maximum,w in regular)*policy.scale
    elif policy.method=='weighted':value=sum(v/maximum*w for v,maximum,w in regular)/sum(w for v,maximum,w in regular)*policy.scale
    else:value=sum(v/maximum for v,maximum,w in regular)/len(regular)*policy.scale
    if recovery is not None:
        if policy.recovery=='best':value=max(value,recovery)
        elif policy.recovery=='replace':value=recovery
        elif policy.recovery=='average':value=(value+recovery)/2
    return value.quantize(Decimal(1).scaleb(-policy.decimals),rounding=ROUND_HALF_UP)


def results(db,member,j):
    p=find(db,m.GradingPolicy,j.policy_id,member)
    lessons=db.scalars(scoped(m.Lesson,member).where(m.Lesson.journal_id==j.id,m.Lesson.cancelled.is_(False))).all()
    assessments=db.scalars(scoped(m.Assessment,member).where(m.Assessment.journal_id==j.id)).all()
    attendance={(a.lesson_id,a.student_id):a.status for a in db.scalars(scoped(m.Attendance,member).where(m.Attendance.lesson_id.in_([l.id for l in lessons])))}
    grades={(g.assessment_id,g.student_id):g.value for g in db.scalars(scoped(m.Grade,member).where(m.Grade.assessment_id.in_([a.id for a in assessments])))}
    eligible_lessons={l.id:{x.id for x in roster(db,member,j,l.date)} for l in lessons}
    eligible_assessments={a.id:{x.id for x in roster(db,member,j,a.date)} for a in assessments}
    output=[]
    for student in roster(db,member,j):
        ls=[l for l in lessons if student.id in eligible_lessons[l.id]]
        regular=[a for a in assessments if a.kind=='regular' and student.id in eligible_assessments[a.id]]
        recoveries=[a for a in assessments if a.kind=='recovery' and student.id in eligible_assessments[a.id]]
        pending=sum((l.id,student.id) not in attendance for l in ls)+sum(grades.get((a.id,student.id)) is None for a in regular)
        if not ls or not regular: pending+=1
        value=None if pending else calculate(p,[(grades[a.id,student.id],a.maximum,a.weight) for a in regular])
        recovery_pending=False
        if value is not None and value<p.passing and p.recovery!='none':
            rec=next((a for a in recoveries if grades.get((a.id,student.id)) is not None),None)
            if rec:value=calculate(p,[(grades[a.id,student.id],a.maximum,a.weight) for a in regular],grades[rec.id,student.id]/rec.maximum*p.scale)
            else:pending+=1;recovery_pending=True
        present=sum(attendance.get((l.id,student.id))=='present' for l in ls)
        frequency=(Decimal(present)*100/len(ls)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if ls else None
        concept=None
        if value is not None and p.method=='concepts':
            concept=next((c['label'] for c in sorted(p.concepts,key=lambda c:Decimal(c['minimum']),reverse=True) if value/p.scale*100>=Decimal(c['minimum'])),None)
        output.append({'student_id':student.id,'name':student.name,'average':str(value) if value is not None else None,'concept':concept,'attendance':str(frequency) if frequency is not None else None,'lessons':len(ls),'absences':len(ls)-present,'pending':pending,'recovery_pending':recovery_pending,'result':'Pendente' if pending else 'Aprovado no período' if value>=p.passing and frequency>=p.attendance_min else 'Abaixo dos critérios do período'})
    return output


@router.post('/journals/{item_id}/close')
def close(item_id:UUID,payload:s.VersionIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,ACADEMIC_WRITERS);j=journal_access(db,member,item_id,payload.version,True)
    rows=results(db,member,j)
    if not rows or any(r['pending'] for r in rows):raise HTTPException(409,'Resolva chamadas, notas e recuperações pendentes antes de fechar.')
    j.status='closed';return changed(db,member,j,'journals.close',j.id)


@router.post('/journals/{item_id}/publish')
def publish(item_id:UUID,payload:s.VersionIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,ACADEMIC_WRITERS);j=journal_access(db,member,item_id,payload.version)
    if j.status!='closed':raise HTTPException(409,'Feche o diário antes de publicar.')
    a=find(db,m.Assignment,j.assignment_id,member);p=find(db,m.GradingPolicy,j.policy_id,member)
    revision=(db.scalar(select(func.max(m.Publication.revision)).where(m.Publication.journal_id==j.id)) or 0)+1
    snapshot={'class':find(db,m.ClassGroup,a.class_id,member).name,'subject':find(db,m.Subject,a.subject_id,member).name,'term':find(db,m.AcademicTerm,j.term_id,member).name,
              'policy':{k:str(v) if isinstance(v,Decimal) else v for k,v in dto(p,'name method scale passing attendance_min decimals recovery concepts').items()},'results':results(db,member,j)}
    create(db,m.Publication,{'journal_id':j.id,'revision':revision,'snapshot':snapshot},member)
    j.status='published';return changed(db,member,j,'journals.publish',j.id)


@router.post('/journals/{item_id}/reopen')
def reopen(item_id:UUID,payload:s.ReopenIn,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,{'director'});j=journal_access(db,member,item_id,payload.version)
    if j.status=='draft':raise HTTPException(409,'O diário já está aberto.')
    create(db,m.JournalReopening,{'journal_id':j.id,'reason':payload.reason,'actor_id':member.user_id},member)
    j.status='draft';return changed(db,member,j,'journals.reopen',j.id)


def family_access(db,member,student_id):
    student=find(db,m.Student,student_id,member)
    if member.role in MANAGERS:return student
    if member.role=='student' and member.student_id==student.id:return student
    if member.role=='guardian' and db.scalar(scoped(m.GuardianLink,member).where(m.GuardianLink.student_id==student.id,m.GuardianLink.guardian_id==member.guardian_id,m.GuardianLink.verified.is_(True))):return student
    raise HTTPException(404,'Aluno não encontrado.')


@router.get('/reports/{student_id}')
def report(student_id:UUID,member=Depends(membership),db:Session=Depends(database,scope='function')):
    student=family_access(db,member,student_id)
    publications=db.scalars(scoped(m.Publication,member).order_by(m.Publication.published_at.desc())).all()
    seen=set();items=[]
    for p in publications:
        if p.journal_id in seen:continue
        seen.add(p.journal_id)
        row=next((r for r in p.snapshot['results'] if r['student_id']==student.id),None)
        valid=[Decimal(r['average']) for r in p.snapshot['results'] if r['average'] is not None and not r['pending']]
        comparison=(sum(valid,Decimal(0))/len(valid)).quantize(Decimal(1).scaleb(-int(p.snapshot['policy']['decimals'])),rounding=ROUND_HALF_UP) if len(valid)>=5 and p.snapshot['policy']['method']!='concepts' else None
        if row:items.append({'id':p.id,'revision':p.revision,'published_at':p.published_at,'class':p.snapshot['class'],'subject':p.snapshot['subject'],'term':p.snapshot['term'],'policy':p.snapshot['policy'],'result':row,'class_average':str(comparison) if comparison is not None else None})
    return {'student':student.name,'items':items}


@router.get('/journals/{item_id}/arrival-suggestions')
def arrival_suggestions(item_id:UUID,date:date,member=Depends(membership),db:Session=Depends(database,scope='function')):
    from datetime import datetime,time
    from zoneinfo import ZoneInfo
    j=journal_access(db,member,item_id);check_date(db,member,j,date)
    students={s.id for s in roster(db,member,j,date)}
    zone=ZoneInfo('America/Sao_Paulo');start=datetime.combine(date,time(),zone);end=start+timedelta(days=1)
    records=scoped(m.ServiceRecord,member).with_only_columns(m.ServiceRecord.id).where(m.ServiceRecord.module=='access',m.ServiceRecord.student_id.in_(students))
    events=db.execute(select(m.ServiceRecord.student_id,m.ServiceEvent.created_at).join(m.ServiceEvent,m.ServiceEvent.record_id==m.ServiceRecord.id).where(m.ServiceRecord.id.in_(records),m.ServiceEvent.action=='transition',m.ServiceEvent.data['to'].as_string()=='entered',m.ServiceEvent.created_at>=start,m.ServiceEvent.created_at<end)).all()
    latest={}
    for sid,timestamp in events:latest[sid]=max(latest.get(sid,timestamp),timestamp)
    return [{'student_id':sid,'suggested_status':'present','recorded_at':timestamp} for sid,timestamp in latest.items()]

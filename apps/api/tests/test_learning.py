from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import engine,tenant_context
from app.learning import calculate
from conftest import authenticate


def setup(client,context):
    h,b=context
    def get(path):return client.get(b+'/'+path,headers=h).json()
    assignment=get('assignments')[0];year=get('academic-years')[0]
    r=client.post(b+'/academic-terms',headers=h,json={'name':'Período de teste','academic_year_id':year['id'],'sequence':1,'start_date':'2026-02-02','end_date':'2026-12-18'})
    assert r.status_code==201,r.text
    term=r.json()
    r=client.post(b+'/grading-policies',headers=h,json={'name':'Média simples','method':'simple','scale':10,'passing':6,'attendance_min':75,'decimals':1,'recovery':'none'})
    assert r.status_code==201,r.text
    policy=r.json()
    r=client.post(b+'/journals',headers=h,json={'assignment_id':assignment['id'],'term_id':term['id'],'policy_id':policy['id']})
    assert r.status_code==201,r.text
    return r.json(),assignment,policy


def detail(client,context,j):
    h,b=context;r=client.get(b+'/journals/'+j['id'],headers=h);assert r.status_code==200,r.text;return r.json()


def complete(client,context,j):
    h,b=context;path=b+'/journals/'+j['id'];d=detail(client,context,j)
    l=client.post(path+'/lessons',headers=h,json={'version':d['version'],'date':'2026-03-01','slot':1,'content':'Números naturais'})
    assert l.status_code==201,l.text
    entries=[{'student_id':s['id'],'status':'present'} for s in d['students']]
    r=client.put(b+'/lessons/'+l.json()['id']+'/attendance',headers=h,json={'version':l.json()['version'],'entries':entries});assert r.status_code==200,r.text
    a=client.post(path+'/assessments',headers=h,json={'version':r.json()['version'],'name':'Prova','date':'2026-03-02','maximum':10,'weight':1});assert a.status_code==201,a.text
    r=client.put(b+'/assessments/'+a.json()['id']+'/grades',headers=h,json={'version':a.json()['version'],'entries':[{'student_id':s['id'],'value':8} for s in d['students']]});assert r.status_code==200,r.text
    return r.json()['version'],l.json(),a.json()


def test_publish_reopen_preserves_snapshot_and_family_revocation(client,context):
    h,b=context;j,_,_=setup(client,context);version,l,a=complete(client,context,j)
    path=b+'/journals/'+j['id']
    r=client.post(path+'/close',headers=h,json={'version':version});assert r.status_code==200,r.text
    assert client.put(b+'/assessments/'+a['id']+'/grades',headers=h,json={'version':r.json()['version'],'entries':[{'student_id':detail(client,context,j)['students'][0]['id'],'value':9}]}).status_code==409
    r=client.post(path+'/publish',headers=h,json={'version':r.json()['version']});assert r.status_code==200,r.text
    guardian=authenticate(client,'guardian@aurora.example.com')
    student=client.get(b+'/portal',headers=guardian).json()['students'][0]
    report=client.get(b+'/reports/'+student['id'],headers=guardian);assert report.status_code==200
    assert report.json()['items'][0]['result']['average']=='8.0'
    published=report.json()
    r=client.post(path+'/reopen',headers=h,json={'version':r.json()['version'],'reason':'Corrigir lançamento conforme revisão.'});assert r.status_code==200,r.text
    assert client.get(b+'/reports/'+student['id'],headers=guardian).json()==published
    link=client.get(b+'/guardian-links',headers=h).json()[0]
    client.delete(b+'/guardian-links/'+link['id'],headers=h)
    assert client.get(b+'/reports/'+student['id'],headers=guardian).status_code==404


def test_batch_validation_stale_version_and_closure_pending(client,context):
    h,b=context;j,_,_=setup(client,context);path=b+'/journals/'+j['id']
    assert client.post(path+'/close',headers=h,json={'version':1}).status_code==409
    assert client.post(path+'/lessons',headers=h,json={'version':1,'date':'2027-01-01','slot':1,'content':'Fora do período'}).status_code==422
    l=client.post(path+'/lessons',headers=h,json={'version':1,'date':'2026-03-01','slot':1,'content':'Conteúdo'}).json()
    assert client.post(path+'/lessons',headers=h,json={'version':1,'date':'2026-03-02','slot':1,'content':'Concorrente'}).status_code==409
    students=detail(client,context,j)['students']
    entries=[{'student_id':students[0]['id'],'status':'present'},{'student_id':'00000000-0000-0000-0000-000000000000','status':'present'}]
    assert client.put(b+'/lessons/'+l['id']+'/attendance',headers=h,json={'version':2,'entries':entries}).status_code==422
    assert detail(client,context,j)['lessons'][0]['attendance']==[]
    assert client.put(b+'/lessons/'+l['id']+'/attendance',headers=h,json={'version':2,'entries':[entries[0],entries[0]]}).status_code==422


def test_diary_permissions_and_rls(client,context):
    h,b=context;j,_,_=setup(client,context)
    for role in ('guardian','student'):
        auth=authenticate(client,role+'@aurora.example.com')
        assert client.get(b+'/journals',headers=auth).status_code==403
        assert client.get(b+'/journals/'+j['id'],headers=auth).status_code==403
    teacher=authenticate(client,'teacher@aurora.example.com')
    assert client.get(b+'/journals/'+j['id'],headers=teacher).status_code==200
    assert client.post(b+'/journals/'+j['id']+'/close',headers=teacher,json={'version':1}).status_code==403
    other=authenticate(client,'director@horizonte.example.com')
    assert client.get(b+'/journals/'+j['id'],headers=other).status_code==404
    with Session(engine) as db,db.begin():
        for table in ('grading_policies','journals','placements'):
            assert db.execute(text(f'SELECT count(*) FROM {table}')).scalar()==0


def test_policy_calculations_and_recovery():
    p=SimpleNamespace(method='simple',scale=Decimal(10),decimals=2,recovery='none')
    values=[(Decimal(5),Decimal(10),Decimal(1)),(Decimal(9),Decimal(10),Decimal(3))]
    assert calculate(p,values)==Decimal('7.00')
    p.method='weighted';assert calculate(p,values)==Decimal('8.00')
    p.method='points';assert calculate(p,[(Decimal(5),Decimal(10),Decimal(1)),(Decimal(15),Decimal(20),Decimal(1))])==Decimal('6.67')
    p.method='simple';p.recovery='best';assert calculate(p,values,Decimal(9))==Decimal('9.00')
    p.recovery='average';assert calculate(p,values,Decimal(9))==Decimal('8.00')
    p.recovery='replace';assert calculate(p,values,Decimal(6))==Decimal('6.00')
    assert calculate(p,[]) is None


def test_transfer_and_reactivation_preserve_intervals(client,context):
    h,b=context;enrollment=client.get(b+'/enrollments',headers=h).json()[0];groups=client.get(b+'/classes',headers=h).json()
    target=next(g for g in groups if g['id']!=enrollment['class_id'])
    path=b+'/enrollments/'+enrollment['id']
    r=client.post(path+'/move',headers=h,json={'action':'transfer','class_id':target['id'],'date':'2026-04-01','reason':'Mudança de horário solicitada.'});assert r.status_code==200,r.text
    history=client.get(path+'/history',headers=h).json()
    assert len(history['placements'])==2
    assert history['placements'][0]['end_date']==history['placements'][1]['start_date']=='2026-04-01'
    assert client.post(path+'/move',headers=h,json={'action':'cancel','date':'2026-05-01','reason':'Transferência externa solicitada.'}).status_code==200
    assert client.post(path+'/move',headers=h,json={'action':'reactivate','date':'2026-04-15','reason':'Retorno solicitado pela família.'}).status_code==422
    assert client.post(path+'/move',headers=h,json={'action':'reactivate','date':'2026-06-01','reason':'Retorno solicitado pela família.'}).status_code==200
    assert len(client.get(path+'/history',headers=h).json()['placements'])==3


def test_sql_grade_bounds_and_concurrent_journal_edit(client,context):
    from concurrent.futures import ThreadPoolExecutor
    import pytest
    from sqlalchemy.exc import DBAPIError
    h,b=context;j,_,_=setup(client,context);version,_,a=complete(client,context,j)
    with pytest.raises(DBAPIError),Session(engine) as db,db.begin():
        tenant_context(db,b.rsplit('/',1)[-1])
        db.execute(text('UPDATE grades SET value=999 WHERE assessment_id=:id'),{'id':a['id']})
    def add(slot):return client.post(b+'/journals/'+j['id']+'/lessons',headers=h,json={'version':version,'date':'2026-04-01','slot':slot,'content':'Alteração concorrente'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(add,[1,2]))==[201,409]

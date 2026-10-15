from test_learning import setup,complete,detail
from conftest import authenticate


def test_annual_requires_published_periods_and_preserves_versions(client,context):
    h,b=context;j,assignment,policy=setup(client,context)
    term=client.get(b+'/academic-terms',headers=h).json()[0];year=client.get(b+'/academic-years',headers=h).json()[0]
    r=client.post(b+'/annual-policies',headers=h,json={'name':'Média anual de teste','academic_year_id':year['id'],'policy_id':policy['id'],'weights':[{'term_id':term['id'],'weight':1}]})
    assert r.status_code==201,r.text
    annual=r.json();student=detail(client,context,j)['students'][0]
    path=b+'/annual-policies/'+annual['id']+'/students/'+student['id']
    assert client.post(path+'/publish',headers=h,json={}).status_code==409
    version,_,_=complete(client,context,j)
    r=client.post(b+'/journals/'+j['id']+'/close',headers=h,json={'version':version});assert r.status_code==200,r.text
    assert client.post(b+'/journals/'+j['id']+'/publish',headers=h,json={'version':r.json()['version']}).status_code==200
    preview=client.get(path,headers=h)
    assert preview.status_code==200,preview.text
    assert preview.json()['results'][0]['average']=='8.0'
    r=client.post(path+'/publish',headers=h,json={});assert r.status_code==200,r.text
    assert r.json()['revision']==1
    assert client.post(path+'/publish',headers=h,json={}).json()['revision']==2
    guardian=authenticate(client,'guardian@aurora.example.com')
    own=client.get(b+'/portal',headers=guardian).json()['students'][0]['id']
    if own==student['id']:assert len(client.get(b+'/annual-reports/'+own,headers=guardian).json())==1
    other=authenticate(client,'director@horizonte.example.com')
    assert client.get(path,headers=other).status_code==404

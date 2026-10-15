from conftest import authenticate


def test_export_search_and_audit_authorization(client,context):
    h,b=context
    name='=Aluno com fórmula'
    r=client.post(b+'/students',headers=h,json={'name':name,'birth_date':'2014-01-01'});assert r.status_code==201
    assert client.get(b+'/search?q=fórmula',headers=h).json()[0]['name']==name
    exported=client.get(b+'/exports/students',headers=h)
    assert exported.status_code==200
    assert "'=Aluno com fórmula" in exported.json()['content']
    assert client.get(b+'/audit?q=exports.students',headers=h).json()
    family=authenticate(client,'guardian@aurora.example.com')
    for path in ('search?q=Aluno','exports/students','audit'):
        assert client.get(b+'/'+path,headers=family).status_code==403
    other=authenticate(client,'director@horizonte.example.com')
    assert client.get(b+'/exports/students',headers=other).status_code==404

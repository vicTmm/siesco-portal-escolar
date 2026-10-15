import base64
import time
from cryptography.fernet import Fernet
from app import accounts,mfa
from conftest import authenticate


def test_password_reset_single_use_revokes_sessions_without_account_enumeration(client,context,monkeypatch):
    h,b=context;captured=[]
    monkeypatch.setenv('EMAIL_DELIVERY','local');monkeypatch.setattr(accounts,'deliver',lambda email,token:captured.append((email,token)))
    response=client.post('/api/v1/auth/forgot-password',json={'email':'director@aurora.example.com'})
    assert response.status_code==200
    assert client.post('/api/v1/auth/forgot-password',json={'email':'absent@example.com'}).json()==response.json()
    token=captured[0][1]
    assert client.post('/api/v1/auth/reset-password',json={'token':token,'password':'NovaSenhaLonga2026!'}).status_code==200
    assert client.get('/api/v1/me',headers=h).status_code==401
    assert client.post('/api/v1/auth/reset-password',json={'token':token,'password':'OutraSenhaLonga2026!'}).status_code==422
    assert client.post('/api/v1/auth/login',json={'email':'director@aurora.example.com','password':'NovaSenhaLonga2026!'}).status_code==200


def test_authenticated_change_requires_current_password(client,context):
    h,b=context
    assert client.post('/api/v1/auth/change-password',headers=h,json={'current_password':'wrong','password':'NovaSenhaLonga2026!'}).status_code==422
    assert client.post('/api/v1/auth/change-password',headers=h,json={'current_password':'asd123','password':'short'}).status_code==422
    # Test environment can use another seed password in CI.
    import os
    assert client.post('/api/v1/auth/change-password',headers=h,json={'current_password':os.environ['DEMO_PASSWORD'],'password':'NovaSenhaLonga2026!'}).status_code==200
    assert client.get('/api/v1/me',headers=h).status_code==401


def test_mfa_rfc_vectors_activation_and_recovery_replay(client,context,monkeypatch):
    secret=base64.b32encode(b'12345678901234567890').decode()
    assert mfa.totp(secret,59//30,8)=='94287082'
    assert mfa.totp(secret,1111111109//30,8)=='07081804'
    h,b=context
    monkeypatch.setenv('APP_ENCRYPTION_KEY',Fernet.generate_key().decode())
    import os
    response=client.post('/api/v1/auth/mfa/setup',headers=h,json={'password':os.environ['DEMO_PASSWORD']})
    assert response.status_code==200,response.text
    secret=response.json()['secret'];code=mfa.totp(secret,int(time.time())//30)
    response=client.post('/api/v1/auth/mfa/confirm',headers=h,json={'code':code})
    assert response.status_code==200,response.text
    recovery=response.json()['recovery_codes'][0]
    assert client.get('/api/v1/me',headers=h).status_code==401
    payload={'email':'director@aurora.example.com','password':os.environ['DEMO_PASSWORD']}
    assert client.post('/api/v1/auth/login',json=payload).status_code==401
    assert client.post('/api/v1/auth/login',json={**payload,'otp':code}).status_code==401  # activation consumed this step
    assert client.post('/api/v1/auth/login',json={**payload,'otp':recovery}).status_code==200
    assert client.post('/api/v1/auth/login',json={**payload,'otp':recovery}).status_code==401


def test_invites_are_director_only(client,context,monkeypatch):
    h,b=context;captured=[]
    monkeypatch.setattr(accounts,'deliver',lambda email,token:captured.append(email))
    account=client.get(b+'/accounts',headers=h).json()[0]
    secretary=authenticate(client,'secretary@aurora.example.com')
    assert client.post(b+'/accounts/'+account['id']+'/invite',headers=secretary).status_code==403
    assert client.post(b+'/accounts/'+account['id']+'/invite',headers=h).status_code==200
    assert captured

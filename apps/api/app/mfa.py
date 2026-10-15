"""TOTP per RFC 6238, encrypted at rest and with one-time recovery codes."""
import base64
import hmac
import hashlib
import os
import struct
import time
from secrets import token_bytes,token_hex
from datetime import datetime,timedelta,timezone
from urllib.parse import quote
from cryptography.fernet import Fernet,InvalidToken
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field
from sqlalchemy import select,delete,func
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database,engine
from .security import current_user,verify_password,hash_token

router=APIRouter(prefix='/api/v1/auth/mfa',tags=['Verificação em duas etapas'])


class PasswordIn(Schema):
    password:str=Field(min_length=1,max_length=128)


class CodeIn(Schema):
    code:str=Field(min_length=6,max_length=64)


class DisableIn(PasswordIn,CodeIn):pass


def cipher():
    key=os.environ.get('APP_ENCRYPTION_KEY')
    if not key:raise HTTPException(503,'A chave de proteção do MFA ainda não foi configurada.')
    try:return Fernet(key.encode())
    except ValueError:raise HTTPException(503,'Configuração de proteção do MFA inválida.')


def totp(secret,step,digits=6):
    digest=hmac.new(base64.b32decode(secret),struct.pack('>Q',step),hashlib.sha1).digest()
    offset=digest[-1]&15
    return str((struct.unpack('>I',digest[offset:offset+4])[0]&0x7fffffff)%(10**digits)).zfill(digits)


def valid_step(secret,code,last=0):
    step=int(time.time())//30
    return next((s for s in (step-1,step,step+1) if s>last and hmac.compare_digest(totp(secret,s),code)),None)


def verify_mfa(user,code):
    if not user.mfa_secret:return True
    try:secret=cipher().decrypt(user.mfa_secret.encode()).decode()
    except InvalidToken:raise HTTPException(503,'Não foi possível verificar o MFA. Contate o suporte.')
    step=valid_step(secret,code,user.mfa_step)
    if step is not None:user.mfa_step=step;return True
    hashed=hash_token(code)
    codes=user.mfa_recovery or []
    if hashed in codes:user.mfa_recovery=[c for c in codes if c!=hashed];return True
    return False


def throttle(db,user):
    key=hash_token('mfa:'+user.id)
    recent=datetime.now(timezone.utc)-timedelta(minutes=10)
    # Persist attempts separately without closing the request transaction.
    with Session(engine) as log,log.begin():
        log.scalar(select(m.User.id).where(m.User.id==user.id).with_for_update())
        if log.scalar(select(func.count()).select_from(m.LoginAttempt).where(m.LoginAttempt.key==key,m.LoginAttempt.occurred_at>recent))>=10:
            raise HTTPException(429,'Muitas tentativas. Aguarde 10 minutos.')
        log.add(m.LoginAttempt(key=key))



@router.get('')
def status(user=Depends(current_user)):
    return {'enabled':bool(user.mfa_secret),'available':bool(os.environ.get('APP_ENCRYPTION_KEY'))}


@router.post('/setup')
def setup(payload:PasswordIn,user=Depends(current_user),db:Session=Depends(database,scope='function')):
    throttle(db,user)
    u=db.scalar(select(m.User).where(m.User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if not verify_password(u.password_hash,payload.password):raise HTTPException(422,'Senha incorreta.')
    if u.mfa_secret:raise HTTPException(409,'MFA já está ativado.')
    secret=base64.b32encode(token_bytes(20)).decode()
    u.mfa_pending=cipher().encrypt(secret.encode()).decode()
    return {'secret':secret,'uri':f'otpauth://totp/SIESCO:{quote(u.email)}?secret={secret}&issuer=SIESCO&digits=6&period=30'}


@router.post('/confirm')
def confirm(payload:CodeIn,user=Depends(current_user),db:Session=Depends(database,scope='function')):
    throttle(db,user)
    u=db.scalar(select(m.User).where(m.User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if not u.mfa_pending or u.mfa_secret:raise HTTPException(422,'Inicie a configuração novamente.')
    try:secret=cipher().decrypt(u.mfa_pending.encode(),ttl=600).decode()
    except InvalidToken:raise HTTPException(422,'Configuração expirada. Inicie novamente.')
    step=valid_step(secret,payload.code)
    if step is None:raise HTTPException(422,'Código inválido.')
    codes=[token_hex(8) for _ in range(8)]
    u.mfa_secret=u.mfa_pending;u.mfa_pending=None;u.mfa_step=step;u.mfa_recovery=[hash_token(c) for c in codes]
    db.execute(delete(m.LoginSession).where(m.LoginSession.user_id==u.id))
    return {'recovery_codes':codes,'message':'MFA ativado. Guarde os códigos e entre novamente.'}


@router.post('/disable')
def disable(payload:DisableIn,user=Depends(current_user),db:Session=Depends(database,scope='function')):
    throttle(db,user)
    u=db.scalar(select(m.User).where(m.User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if not u.mfa_secret or not verify_password(u.password_hash,payload.password) or not verify_mfa(u,payload.code):raise HTTPException(422,'Senha ou código inválidos.')
    u.mfa_secret=None;u.mfa_pending=None;u.mfa_step=0;u.mfa_recovery=[]
    db.execute(delete(m.LoginSession).where(m.LoginSession.user_id==u.id))
    return {'message':'MFA desativado. Entre novamente.'}

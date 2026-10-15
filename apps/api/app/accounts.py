"""Single-use password recovery, invitations and authenticated password changes."""
import os
import smtplib
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime,timedelta,timezone
from secrets import token_urlsafe
from uuid import UUID
from pydantic import EmailStr,Field
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,delete,func
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .security import current_user,password_hasher,verify_password,hash_token,membership,permit
from .domain import audit

router=APIRouter(prefix='/api/v1',tags=['Acesso e recuperação'])


class ResetRequest(Schema):
    email:EmailStr


class ResetIn(Schema):
    token:str=Field(min_length=32,max_length=128)
    password:str=Field(min_length=12,max_length=128)


class ChangeIn(Schema):
    current_password:str=Field(min_length=1,max_length=128)
    password:str=Field(min_length=12,max_length=128)


def deliver(email,token):
    origin=os.environ.get('PUBLIC_APP_URL','http://localhost:3100').rstrip('/')
    if not origin.startswith(('https://','http://localhost:')):raise HTTPException(503,'Configure PUBLIC_APP_URL com HTTPS.')
    message=EmailMessage();message['From']=os.environ.get('SMTP_FROM','siesco@localhost');message['To']=email;message['Subject']='Defina sua senha no SIESCO'
    message.set_content(f'Para definir sua senha, abra {origin}/#reset_token={token}\nO link é válido por 30 minutos e pode ser usado uma vez. Se não solicitou, ignore.')
    if os.environ.get('EMAIL_DELIVERY')=='local':
        target=Path(os.environ.get('LOCAL_MAIL_DIR','../../.local/mail'));target.mkdir(mode=0o700,parents=True,exist_ok=True)
        file=target/(token_urlsafe(12)+'.eml')
        fd=os.open(file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write(message.as_string())
        return
    host=os.environ.get('SMTP_HOST')
    if not host:raise HTTPException(503,'O envio de e-mails ainda não foi configurado.')
    try:
        with smtplib.SMTP(host,int(os.environ.get('SMTP_PORT','587')),timeout=10) as smtp:
            smtp.starttls()
            if os.environ.get('SMTP_USER'):smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
            smtp.send_message(message)
    except (OSError,smtplib.SMTPException):raise HTTPException(503,'Não foi possível enviar o e-mail. Tente mais tarde.')


def issue_reset(db,user):
    user=db.scalar(select(m.User).where(m.User.id==user.id).with_for_update())
    db.execute(delete(m.PasswordReset).where(m.PasswordReset.user_id==user.id))
    token=token_urlsafe(48)
    db.add(m.PasswordReset(user_id=user.id,token_hash=hash_token(token),expires_at=datetime.now(timezone.utc)+timedelta(minutes=30)))
    deliver(user.email,token)


@router.post('/auth/forgot-password')
def forgot(payload:ResetRequest,db:Session=Depends(database,scope='function')):
    # Same response for unknown and existing addresses; throttle before lookup.
    key=hash_token('reset:'+str(payload.email).lower());recent=datetime.now(timezone.utc)-timedelta(minutes=30)
    if db.scalar(select(func.count()).select_from(m.LoginAttempt).where(m.LoginAttempt.key==key,m.LoginAttempt.occurred_at>recent))>=3:raise HTTPException(429,'Aguarde antes de solicitar outro link.')
    db.add(m.LoginAttempt(key=key));db.flush()
    if not os.environ.get('SMTP_HOST') and os.environ.get('EMAIL_DELIVERY')!='local':raise HTTPException(503,'O envio de e-mails ainda não foi configurado.')
    user=db.scalar(select(m.User).where(m.User.email==str(payload.email).lower(),m.User.active.is_(True)))
    if user:issue_reset(db,user)
    return {'message':'Se houver uma conta ativa, você receberá um link para definir sua senha.'}


@router.post('/auth/reset-password')
def reset(payload:ResetIn,db:Session=Depends(database,scope='function')):
    # Serialize competing requests on the user as well as on the token.
    candidate=db.scalar(select(m.PasswordReset).where(m.PasswordReset.token_hash==hash_token(payload.token)))
    if not candidate:raise HTTPException(422,'Link inválido ou expirado.')
    user=db.scalar(select(m.User).where(m.User.id==candidate.user_id).with_for_update())
    record=db.scalar(select(m.PasswordReset).where(m.PasswordReset.id==candidate.id).with_for_update().execution_options(populate_existing=True))
    if not record or record.used or record.expires_at<=datetime.now(timezone.utc) or not user.active:raise HTTPException(422,'Link inválido ou expirado.')
    record.used=True;user.password_hash=password_hasher.hash(payload.password)
    db.execute(delete(m.LoginSession).where(m.LoginSession.user_id==user.id))
    return {'message':'Senha definida. Entre novamente no portal.'}


@router.post('/auth/change-password')
def change(payload:ChangeIn,user=Depends(current_user),db:Session=Depends(database,scope='function')):
    locked=db.scalar(select(m.User).where(m.User.id==user.id).with_for_update())
    if not verify_password(locked.password_hash,payload.current_password):raise HTTPException(422,'Senha atual incorreta.')
    locked.password_hash=password_hasher.hash(payload.password)
    db.execute(delete(m.LoginSession).where(m.LoginSession.user_id==user.id))
    return {'message':'Senha alterada. Entre novamente.'}


@router.post('/institutions/{institution_id}/accounts/{item_id}/invite')
def invite(item_id:UUID,member=Depends(membership),db:Session=Depends(database,scope='function')):
    permit(member,{'director'})
    account=db.scalar(select(m.Membership).where(m.Membership.id==str(item_id),m.Membership.institution_id==member.institution_id,m.Membership.school_id==member.school_id))
    if not account:raise HTTPException(404,'Conta não encontrada.')
    user=db.get(m.User,account.user_id)
    if not user.active:raise HTTPException(409,'Conta inativa.')
    issue_reset(db,user);audit(db,member,'accounts.invite',account.id)
    return {'message':'Convite para definir senha enviado.'}

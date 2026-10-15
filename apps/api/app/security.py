from datetime import datetime, timezone
import os
from hashlib import sha256

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import database, tenant_context
from .models import LoginSession, Membership, User

password_hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
DUMMY_HASH = password_hasher.hash("not-a-user-password")


def hash_token(value):
    return sha256(value.encode()).hexdigest()


def verify_password(hashed, password):
    try:
        return password_hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(database, scope="function")):
    if not credentials:
        raise HTTPException(401, "Entre para continuar.")
    session = db.scalar(select(LoginSession).where(LoginSession.token_hash == hash_token(credentials.credentials), LoginSession.expires_at > datetime.now(timezone.utc)))
    user = db.get(User, session.user_id) if session else None
    if not user or not user.active:
        raise HTTPException(401, "Sessão expirada ou inválida.")
    return user


def require_platform(user: User = Depends(current_user)):
    if not user.platform_admin:
        raise HTTPException(403, "Acesso restrito à administração da plataforma.")
    if os.environ.get("REQUIRE_STAFF_MFA") == "true" and not user.mfa_secret:
        raise HTTPException(403, "Configure a verificação em duas etapas em Minha senha.")
    return user


def membership(institution_id: str, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    member = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.institution_id == institution_id))
    if not member:
        raise HTTPException(404, "Instituição não encontrada.")
    if os.environ.get("REQUIRE_STAFF_MFA") == "true" and member.role in {"director", "coordinator", "secretary", "teacher"} and not user.mfa_secret:
        raise HTTPException(403, "Configure a verificação em duas etapas em Minha senha.")
    tenant_context(db, institution_id)
    return member


def permit(member, roles):
    if member.role not in roles:
        raise HTTPException(403, "Seu perfil não permite esta operação.")


MANAGERS = {"director", "coordinator", "secretary"}
PEOPLE_WRITERS = {"director", "secretary"}
ACADEMIC_WRITERS = {"director", "coordinator"}

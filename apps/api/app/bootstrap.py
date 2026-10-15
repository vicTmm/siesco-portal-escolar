"""Create the first platform administrator without demo data or implicit resets."""
import os
from pydantic import EmailStr,TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import engine
from .models import User
from .security import password_hasher


def bootstrap():
    email=str(TypeAdapter(EmailStr).validate_python(os.environ['BOOTSTRAP_ADMIN_EMAIL'])).lower()
    password=os.environ['BOOTSTRAP_ADMIN_PASSWORD']
    if len(password)<16:raise RuntimeError('Senha de bootstrap exige ao menos 16 caracteres.')
    with Session(engine) as db,db.begin():
        if db.scalar(select(User.id).where(User.platform_admin.is_(True))):raise RuntimeError('Administrador já existe; nenhuma conta alterada.')
        db.add(User(name='Administração da plataforma',email=email,password_hash=password_hasher.hash(password),platform_admin=True))
    print('Administrador inicial criado. Configure MFA antes de administrar instituições.')


if __name__=='__main__':bootstrap()

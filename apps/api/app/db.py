import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


engine = create_engine(os.environ.get("DATABASE_URL", "postgresql+psycopg://portal_app:local_app@localhost:5432/portal"), pool_pre_ping=True)


def database():
    with Session(engine) as session:
        with session.begin():
            yield session


def tenant_context(db: Session, institution_id: str):
    db.execute(text("SELECT set_config('app.institution_id', :tenant, true)"), {"tenant": institution_id})

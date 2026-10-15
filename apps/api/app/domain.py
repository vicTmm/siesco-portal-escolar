"""Shared tenant-scoped persistence and transactional audit helpers."""
from fastapi import HTTPException
from sqlalchemy import select

from . import models as m


def scoped(model, member):
    return select(model).where(model.institution_id == member.institution_id, model.school_id == member.school_id)


def find(db, model, item_id, member, lock=False):
    statement = scoped(model, member).where(model.id == str(item_id))
    item = db.scalar(statement.with_for_update().execution_options(populate_existing=True) if lock else statement)
    if not item:
        raise HTTPException(404, "Registro não encontrado.")
    return item


def audit(db, member, action, item_id):
    db.add(m.AuditEvent(institution_id=member.institution_id, school_id=member.school_id,
                       actor_id=member.user_id, action=action, entity_id=item_id))


def create(db, model, values, member):
    item = model(**values, institution_id=member.institution_id, school_id=member.school_id)
    db.add(item)
    db.flush()
    audit(db, member, model.__tablename__ + ".create", item.id)
    db.flush()
    return item

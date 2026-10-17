from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import audit
from .security import membership, permit

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Unidades escolares"]
)


class UnitIn(Schema):
    name: str = Field(min_length=3, max_length=160)


@router.post("/units", status_code=201)
def add(
    payload: UnitIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director"})
    unit = m.School(institution_id=member.institution_id, name=payload.name)
    db.add(unit)
    db.flush()
    db.add(
        m.Membership(
            institution_id=member.institution_id,
            school_id=unit.id,
            user_id=member.user_id,
            role="director",
        )
    )
    audit(db, member, "units.create", unit.id)
    return {
        "id": unit.id,
        "name": unit.name,
        "message": "Unidade criada. Entre novamente para selecionar seu novo acesso.",
    }

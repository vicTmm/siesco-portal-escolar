"""Private PDF/JPEG/PNG attachments with fresh record authorization on every download."""

import base64
import binascii
import hashlib
import re
import io
from PIL import Image as PillowImage, UnidentifiedImageError
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find, create, audit
from .security import membership, permit, MANAGERS
from .services import access_record, PRIVATE_TYPES, FAMILY_CREATE, allowed
from .mfa import cipher

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Anexos privados"]
)


class UploadIn(Schema):
    filename: str = Field(min_length=1, max_length=120)
    base64: str = Field(max_length=2800000)


@router.post("/service-records/{item_id}/attachments", status_code=201)
def upload(
    item_id: UUID,
    payload: UploadIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, MANAGERS | {"teacher", "guardian"})
    r = access_record(db, member, item_id)
    if member.role == "teacher" or (
        member.role in MANAGERS
        and r.module in {"books", "office_hours", "knowledge", "calendar"}
    ):
        allowed(db, member, r.module, r.student_id, True, r)
    if member.role == "guardian" and r.module not in FAMILY_CREATE | PRIVATE_TYPES:
        raise HTTPException(403, "Anexos indisponíveis para este perfil.")
    try:
        content = base64.b64decode(payload.base64, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, "Arquivo inválido.")
    if not 1 <= len(content) <= 2 * 1024 * 1024:
        raise HTTPException(422, "O arquivo deve ter até 2 MB.")
    mime = (
        "application/pdf"
        if content.startswith(b"%PDF-")
        else "image/png"
        if content.startswith(b"\x89PNG\r\n\x1a\n")
        else "image/jpeg"
        if content.startswith(b"\xff\xd8\xff")
        else None
    )
    if not mime:
        raise HTTPException(422, "Envie um PDF, PNG ou JPEG.")
    if mime in {"image/png", "image/jpeg"}:
        try:
            with PillowImage.open(io.BytesIO(content)) as image:
                if (
                    image.width > 8000
                    or image.height > 8000
                    or image.width * image.height > 16000000
                ):
                    raise ValueError()
                image.verify()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            PillowImage.DecompressionBombError,
        ):
            raise HTTPException(
                422,
                "Imagem inválida ou grande demais. Use até 16 megapixels e 8000 pixels por lado.",
            )
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", payload.filename)
    if r.module in PRIVATE_TYPES:
        name = (
            "anexo-confidencial."
            + {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}[mime]
        )
    a = create(
        db,
        m.PrivateAttachment,
        {
            "record_id": r.id,
            "filename": name,
            "mime_type": mime,
            "sha256": hashlib.sha256(content).hexdigest(),
            "content": cipher().encrypt(content)
            if r.module in PRIVATE_TYPES
            else content,
            "uploader_id": member.user_id,
        },
        member,
    )
    return {"id": a.id, "filename": a.filename}


@router.get("/service-records/{item_id}/attachments")
def attachments(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    r = access_record(db, member, item_id)
    if r.module in PRIVATE_TYPES:
        audit(db, member, "attachments.sensitive_list", r.id)
    return [
        {
            "id": a.id,
            "filename": a.filename,
            "mime_type": a.mime_type,
            "created_at": a.created_at,
        }
        for a in db.scalars(
            scoped(m.PrivateAttachment, member).where(
                m.PrivateAttachment.record_id == r.id
            )
        )
    ]


@router.get("/attachments/{item_id}/download")
def download(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    a = find(db, m.PrivateAttachment, item_id, member)
    r = access_record(db, member, a.record_id)
    content = cipher().decrypt(a.content) if r.module in PRIVATE_TYPES else a.content
    audit(db, member, "attachments.download", a.id)
    return {
        "filename": a.filename,
        "mime_type": a.mime_type,
        "base64": base64.b64encode(content).decode(),
        "sha256": a.sha256,
    }

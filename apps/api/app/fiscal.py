"""Private fiscal drafts and durable national NFS-e submission/reconciliation."""

import hashlib
import gzip
import json
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models as m, nfse_national as national
from .db import database, engine, tenant_context
from .domain import scoped, find, create, audit
from .mfa import cipher
from .schemas import Schema
from .security import membership, permit

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}/fiscal", tags=["NFS-e Nacional"]
)
ROLES = {"director", "secretary"}


def valid_tax_id(value):
    if not value.isascii() or not value.isdigit() or len(set(value)) == 1:
        return False
    if len(value) == 11:
        for length in (9, 10):
            digit = (
                sum(int(v) * (length + 1 - i) for i, v in enumerate(value[:length]))
                * 10
            ) % 11
            if int(value[length]) != (0 if digit == 10 else digit):
                return False
        return True
    if len(value) == 14:
        for length, weights in [
            (12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
            (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
        ]:
            remainder = sum(int(v) * w for v, w in zip(value[:length], weights)) % 11
            if int(value[length]) != (0 if remainder < 2 else 11 - remainder):
                return False
        return True
    return False


class ProfileIn(Schema):
    version: int = Field(ge=0)
    cnpj: str = Field(pattern=r"^[0-9]{14}$")
    legal_name: str = Field(min_length=3, max_length=150)
    municipality_code: str = Field(pattern=r"^[0-9]{7}$", default="3304904")
    municipal_registration: str = Field(default="", max_length=15)
    environment: Literal["test", "production"] = "test"
    series: int = Field(ge=1, le=49999)
    next_number: int = Field(ge=1, le=999999999999999)
    service_code: str = Field(pattern=r"^[0-9]{6}$")
    municipal_service_code: str = Field(default="", pattern=r"^(?:[0-9]{3})?$")
    nbs_code: str = Field(default="", pattern=r"^(?:[0-9]{9})?$")
    simple_national: Literal[1, 2, 3]
    simple_apportionment: Literal[1, 2, 3] = 1
    special_regime: Literal[0, 1, 2, 3, 4, 5, 6, 9]
    total_tax_percent: Decimal = Field(ge=0, le=100, decimal_places=2)
    federal_tax_percent: Decimal = Field(
        default=Decimal(0), ge=0, le=100, decimal_places=2
    )
    state_tax_percent: Decimal = Field(
        default=Decimal(0), ge=0, le=100, decimal_places=2
    )
    municipal_tax_percent: Decimal = Field(
        default=Decimal(0), ge=0, le=100, decimal_places=2
    )
    accounting_confirmed: Literal[True]

    @field_validator("cnpj")
    @classmethod
    def cnpj_valid(cls, v):
        if not valid_tax_id(v):
            raise ValueError("CNPJ inválido.")
        return v

    @model_validator(mode="after")
    def supported(self):
        if self.simple_national != 3:
            raise ValueError(
                "O fluxo inicial contempla ME/EPP optante pelo Simples Nacional. Outros regimes dependem de desenvolvimento e homologação tributária adicionais."
            )
        if self.simple_national == 3 and self.simple_apportionment != 1:
            raise ValueError(
                "Esta versão atende Simples com tributos apurados no Simples Nacional. Regimes híbridos exigem homologação adicional."
            )
        if self.special_regime != 0:
            raise ValueError(
                "Regimes especiais precisam de configuração e homologação adicionais; não emita como regime comum."
            )
        return self


class InvoiceIn(Schema):
    key: UUID
    profile_version: int = Field(ge=1)
    student_id: UUID
    guardian_id: UUID
    tax_id: str = Field(pattern=r"^(?:[0-9]{11}|[0-9]{14})$")
    competence: date
    amount_cents: int = Field(ge=1, le=1000000000)
    description: str = Field(min_length=5, max_length=2000)
    postal_code: str = Field(pattern=r"^[0-9]{8}$")
    municipality_code: str = Field(pattern=r"^[0-9]{7}$")
    street: str = Field(min_length=2, max_length=255)
    street_number: str = Field(min_length=1, max_length=60)
    district: str = Field(min_length=2, max_length=60)

    @field_validator("tax_id")
    @classmethod
    def cpf_cnpj(cls, v):
        if not valid_tax_id(v):
            raise ValueError("CPF/CNPJ do tomador inválido.")
        return v

    @field_validator("competence")
    @classmethod
    def past(cls, v):
        if v > date.today() or v.year < 2000:
            raise ValueError("Informe competência passada ou atual.")
        return v


class VersionIn(Schema):
    version: int = Field(ge=1)


def seal(value):
    return cipher().encrypt(json.dumps(value, ensure_ascii=False).encode())


def unseal(value):
    return json.loads(cipher().decrypt(value))


def message(text):
    return cipher().encrypt(text[:500].encode()).decode()


def profile_data(profile):
    return unseal(profile.encrypted)


def profile_dto(profile):
    return {
        "version": profile.version,
        "next_number": profile.next_number,
        **profile_data(profile),
    }


def invoice_dto(record):
    content = unseal(record.encrypted)
    official_number = None
    if record.authorized_xml:
        root = national.E.fromstring(
            cipher().decrypt(record.authorized_xml), parser=national.PARSER()
        )
        official_number = root.findtext(
            "{" + national.NS + "}infNFSe/{" + national.NS + "}nNFSe"
        )
    return {
        "id": record.id,
        "version": record.version,
        "student": content["student"],
        "guardian": content["guardian"],
        "environment": record.environment,
        "series": record.series,
        "number": record.number,
        "dps_id": record.dps_id,
        "status": record.status,
        "message": cipher().decrypt(record.message.encode()).decode(),
        "access_key": record.access_key,
        "official_number": official_number,
        "created_at": record.created_at,
        "request": content["request"],
    }


@router.get("/profile")
def get_profile(
    member=Depends(membership), db: Session = Depends(database, scope="function")
):
    permit(member, ROLES)
    profile = db.scalar(scoped(m.FiscalProfile, member))
    return profile_dto(profile) if profile else None


@router.put("/profile")
def save_profile(
    payload: ProfileIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, {"director"})
    db.scalar(select(m.School).where(m.School.id == member.school_id).with_for_update())
    profile = db.scalar(scoped(m.FiscalProfile, member).with_for_update())
    if payload.version != (profile.version if profile else 0):
        raise HTTPException(
            409, "Cadastro fiscal atualizado por outra pessoa. Recarregue."
        )
    if (
        profile
        and (profile.cnpj, profile.environment, profile.series)
        == (payload.cnpj, payload.environment, payload.series)
        and payload.next_number < profile.next_number
    ):
        raise HTTPException(409, "A numeração da DPS não pode retroceder.")
    data = payload.model_dump(mode="json", exclude={"version", "next_number"})
    if profile:
        profile.cnpj = payload.cnpj
        profile.environment = payload.environment
        profile.series = payload.series
        profile.next_number = payload.next_number
        profile.encrypted = seal(data)
        profile.version += 1
        audit(db, member, "fiscal.profile_update", profile.id)
    else:
        profile = create(
            db,
            m.FiscalProfile,
            {
                "cnpj": payload.cnpj,
                "environment": payload.environment,
                "series": payload.series,
                "next_number": payload.next_number,
                "encrypted": seal(data),
                "version": 1,
            },
            member,
        )
    return profile_dto(profile)


@router.get("/guardians/{student_id}")
def guardians(
    student_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, ROLES)
    find(db, m.Student, student_id, member)
    ids = (
        scoped(m.GuardianLink, member)
        .with_only_columns(m.GuardianLink.guardian_id)
        .where(
            m.GuardianLink.student_id == str(student_id),
            m.GuardianLink.verified.is_(True),
        )
    )
    return [
        {"id": g.id, "name": g.name}
        for g in db.scalars(
            scoped(m.Guardian, member)
            .where(m.Guardian.id.in_(ids))
            .order_by(m.Guardian.name, m.Guardian.id)
        )
    ]


@router.get("/invoices")
def list_invoices(
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, ROLES)
    audit(db, member, "fiscal.list", member.school_id)
    return [
        invoice_dto(r)
        for r in db.scalars(
            scoped(m.FiscalInvoice, member)
            .order_by(m.FiscalInvoice.created_at.desc(), m.FiscalInvoice.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/invoices", status_code=201)
def draft(
    payload: InvoiceIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, ROLES)
    profile = db.scalar(scoped(m.FiscalProfile, member).with_for_update())
    if not profile:
        raise HTTPException(
            409,
            "A direção precisa preencher o cadastro fiscal antes de preparar notas.",
        )
    data = payload.model_dump(mode="json")
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    existing = db.scalar(
        scoped(m.FiscalInvoice, member).where(m.FiscalInvoice.key == str(payload.key))
    )
    if existing:
        if existing.payload_hash != fingerprint:
            raise HTTPException(
                409, "Esta chave já foi usada em outro rascunho fiscal."
            )
        return invoice_dto(existing)
    if payload.profile_version != profile.version:
        raise HTTPException(
            409,
            "O cadastro fiscal ou a numeração foi atualizado. Atualize as notas e confira os dados antes de preparar o rascunho.",
        )
    student = find(db, m.Student, payload.student_id, member)
    guardian = find(db, m.Guardian, payload.guardian_id, member)
    if not db.scalar(
        scoped(m.GuardianLink, member).where(
            m.GuardianLink.student_id == student.id,
            m.GuardianLink.guardian_id == guardian.id,
            m.GuardianLink.verified.is_(True),
        )
    ):
        raise HTTPException(
            422, "O tomador deve ser um responsável com vínculo verificado ao aluno."
        )
    if profile.next_number >= 999999999999999:
        raise HTTPException(409, "Configure outra série antes de esgotar a numeração.")
    number = profile.next_number
    profile.next_number += 1
    profile.version += 1
    content = {
        "profile": profile_data(profile),
        "request": data,
        "student": student.name,
        "guardian": guardian.name,
    }
    dps_id = (
        "DPS"
        + content["profile"]["municipality_code"]
        + "2"
        + profile.cnpj
        + str(profile.series).zfill(5)
        + str(number).zfill(15)
    )
    record = create(
        db,
        m.FiscalInvoice,
        {
            "student_id": student.id,
            "guardian_id": guardian.id,
            "actor_id": member.user_id,
            "key": str(payload.key),
            "payload_hash": fingerprint,
            "environment": profile.environment,
            "cnpj": profile.cnpj,
            "series": profile.series,
            "number": number,
            "dps_id": dps_id,
            "encrypted": seal(content),
            "status": "draft",
            "message": message("Rascunho fiscal. Ainda não enviado nem autorizado."),
            "version": 1,
        },
        member,
    )
    try:
        national.build_dps(record, content)
    except (ValueError, national.E.DocumentInvalid, national.E.XMLSyntaxError):
        raise HTTPException(
            422,
            "Os dados não atendem ao layout oficial da DPS. Revise cadastro fiscal, endereço e serviço com o contador.",
        )
    return invoice_dto(record)


def fresh_member(db, member):
    tenant_context(db, member.institution_id)
    current = db.scalar(
        select(m.Membership)
        .join(m.User, m.User.id == m.Membership.user_id)
        .where(
            m.Membership.id == member.id,
            m.Membership.user_id == member.user_id,
            m.User.active.is_(True),
        )
    )
    if not current:
        raise HTTPException(403, "Acesso fiscal revogado.")
    permit(current, ROLES)
    return current


def finish(identifier, member, result, status, text):
    with Session(engine) as db, db.begin():
        tenant_context(db, member.institution_id)
        row = find(db, m.FiscalInvoice, identifier, member, lock=True)
        if row.status == "authorized":
            return invoice_dto(row)
        if result:
            row.access_key, xml = result
            row.authorized_xml = cipher().encrypt(xml)
            row.status = "authorized"
            row.message = message(
                "Autorizada em homologação. Sem validade fiscal."
                if row.environment == "test"
                else "NFS-e autorizada pelo emissor nacional."
            )
        else:
            row.status = status
            row.message = message(text)
        row.version += 1
        audit(db, member, "fiscal." + row.status, row.id)
        return invoice_dto(row)


@router.post("/invoices/{item_id}/emit")
def emit(item_id: UUID, payload: VersionIn, member=Depends(membership)):
    permit(member, ROLES)
    with Session(engine) as db, db.begin():
        member = fresh_member(db, member)
        row = find(db, m.FiscalInvoice, item_id, member, lock=True)
        if row.status == "authorized":
            return invoice_dto(row)
        if row.version != payload.version or row.status != "draft":
            raise HTTPException(
                409,
                "A nota foi atualizada ou já enviada. Consulte o retorno antes de reenviar.",
            )
        cert, key, context = national.credentials(
            member.school_id, row.cnpj, row.environment
        )
        content = unseal(row.encrypted)
        try:
            xml = (
                cipher().decrypt(row.signed_xml)
                if row.signed_xml
                else national.sign_dps(national.build_dps(row, content), cert, key)
            )
        except (ValueError, national.E.DocumentInvalid, national.E.XMLSyntaxError):
            raise HTTPException(
                422,
                "Falha ao validar ou assinar a DPS. Revise os dados e o certificado.",
            )
        row.signed_xml = (
            cipher().encrypt(xml) if row.signed_xml is None else row.signed_xml
        )
        row.status = "submitting"
        row.message = message(
            "DPS enviada para processamento; consulte o retorno se houver interrupção."
        )
        row.version += 1
        environment = row.environment
        # Stable identifiers and signed bytes survive a process crash before/after the remote call.
        db.flush()
        db.expunge(row)
        db.expunge(member)
    try:
        response = national.request(environment, context, "POST", "/nfse", xml)
        result = national.authorized_result(response, row, xml)
        if result:
            return finish(item_id, member, result, "authorized", "")
        if 400 <= response.status_code < 500 and response.status_code not in {
            408,
            409,
            429,
        }:
            errors = response.json().get("erros", [])
            description = "; ".join(
                str(
                    e.get(
                        "Descricao",
                        e.get("descricao", e.get("mensagem", "Rejeição fiscal")),
                    )
                )
                for e in errors
            )[:450]
            return finish(
                item_id,
                member,
                None,
                "rejected",
                "Emissor rejeitou a DPS. " + description,
            )
    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        OverflowError,
        gzip.BadGzipFile,
        national.E.LxmlError,
    ):
        pass
    return finish(
        item_id,
        member,
        None,
        "unknown",
        "Não foi possível confirmar o resultado. Consulte o retorno pela mesma DPS antes de tentar novamente.",
    )


@router.post("/invoices/{item_id}/reconcile")
def reconcile(item_id: UUID, payload: VersionIn, member=Depends(membership)):
    permit(member, ROLES)
    with Session(engine) as db, db.begin():
        member = fresh_member(db, member)
        row = find(db, m.FiscalInvoice, item_id, member, lock=True)
        if row.status == "authorized":
            return invoice_dto(row)
        if row.version != payload.version or row.status not in {
            "unknown",
            "submitting",
        }:
            raise HTTPException(
                409, "A nota não está aguardando confirmação ou foi atualizada."
            )
        _, _, context = national.credentials(
            member.school_id, row.cnpj, row.environment
        )
        db.expunge(row)
        db.expunge(member)
    try:
        response = national.request(
            row.environment, context, "GET", "/dps/" + row.dps_id
        )
        if response.status_code == 404:
            return finish(
                item_id,
                member,
                None,
                "draft",
                "O emissor não encontrou esta DPS. Você pode reenviar a mesma declaração, preservando a numeração.",
            )
        response.raise_for_status()
        key = response.json()["chaveAcesso"]
        if not isinstance(key, str) or not national.re.fullmatch(r"[0-9]{50}", key):
            raise ValueError()
        response = national.request(row.environment, context, "GET", "/nfse/" + key)
        result = national.authorized_result(
            response, row, cipher().decrypt(row.signed_xml)
        )
        if result:
            return finish(item_id, member, result, "authorized", "")
    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        gzip.BadGzipFile,
        national.E.LxmlError,
    ):
        pass
    return finish(
        item_id,
        member,
        None,
        "unknown",
        "A consulta ainda não confirmou a autorização. A DPS foi preservada; consulte novamente.",
    )


@router.get("/invoices/{item_id}/xml")
def download_xml(
    item_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    import base64

    permit(member, ROLES)
    row = find(db, m.FiscalInvoice, item_id, member)
    if row.status != "authorized" or not row.authorized_xml:
        raise HTTPException(409, "Ainda não há XML autorizado para esta nota.")
    audit(db, member, "fiscal.download_xml", row.id)
    return {
        "filename": ("HOMOLOGACAO-" if row.environment == "test" else "")
        + "NFSe-"
        + row.access_key
        + ".xml",
        "base64": base64.b64encode(cipher().decrypt(row.authorized_xml)).decode(),
    }

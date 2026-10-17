"""Private prepaid ledgers, catalog stock and manual school settlement. No external payments."""

import hashlib
import json
import re
from datetime import datetime, time, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, model_validator
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from . import models as m
from .schemas import Schema
from .db import database
from .domain import scoped, find, create, audit
from .security import membership, permit
from .learning import family_access
from .mfa import cipher

router = APIRouter(
    prefix="/api/v1/institutions/{institution_id}", tags=["Carteira, cantina e loja"]
)
STAFF = {"director", "secretary"}


class ProductIn(Schema):
    channel: Literal["canteen", "store"]
    code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=2, max_length=160)
    price_cents: int = Field(ge=1, le=10000000)
    stock: int = Field(ge=0, le=1000000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    active: bool = True

    @model_validator(mode="after")
    def valid(self):
        if any(not re.fullmatch(r"[a-z0-9_-]{1,30}", tag) for tag in self.tags) or len(
            set(self.tags)
        ) != len(self.tags):
            raise ValueError(
                "Marcadores distintos, sem espaços, em letras minúsculas (até 30 caracteres)."
            )
        return self


class ProductChange(ProductIn):
    version: int = Field(ge=1)
    note: str = Field(min_length=3, max_length=1000)


class PolicyIn(Schema):
    version: int = Field(ge=0)
    daily_limit_cents: int | None = Field(default=None, ge=0, le=10000000)
    blocked_tags: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def tags(self):
        if len(set(self.blocked_tags)) != len(self.blocked_tags) or any(
            not re.fullmatch(r"[a-z0-9_-]{1,30}", tag) for tag in self.blocked_tags
        ):
            raise ValueError("Marcadores inválidos.")
        return self


class CreditIn(Schema):
    key: UUID
    amount_cents: int = Field(ge=1, le=10000000)
    note: str = Field(min_length=3, max_length=1000)


class LineIn(Schema):
    version: int = Field(ge=1)
    product_id: UUID
    quantity: int = Field(ge=1, le=100)


class PurchaseIn(Schema):
    key: UUID
    channel: Literal["canteen", "store"]
    lines: list[LineIn] = Field(min_length=1, max_length=30)


class RefundIn(Schema):
    key: UUID
    note: str = Field(min_length=10, max_length=1000)
    restock: bool = False


class DeliveryIn(Schema):
    version: int = Field(ge=1)
    note: str = Field(min_length=3, max_length=1000)


def wallet_access(db, member, student_id, lock=False):
    permit(member, STAFF | {"guardian", "student"})
    family_access(db, member, student_id)
    return find(db, m.Student, student_id, member, lock=lock)


def product_dto(p):
    return {
        "id": p.id,
        "channel": p.channel,
        "code": p.code,
        "name": p.name,
        "price_cents": p.price_cents,
        "stock": p.stock,
        "tags": p.tags,
        "active": p.active,
        "version": p.version,
    }


def balance(db, member, student_id):
    return db.scalar(
        scoped(m.WalletEntry, member)
        .with_only_columns(
            func.coalesce(
                func.sum(
                    case(
                        (m.WalletEntry.kind == "debit", -m.WalletEntry.amount_cents),
                        else_=m.WalletEntry.amount_cents,
                    )
                ),
                0,
            )
        )
        .where(m.WalletEntry.student_id == str(student_id))
    )


def policy(db, member, student_id):
    p = db.scalar(
        scoped(m.WalletPolicy, member).where(
            m.WalletPolicy.student_id == str(student_id)
        )
    )
    return (
        {**json.loads(cipher().decrypt(p.encrypted)), "version": p.version}
        if p
        else {"daily_limit_cents": None, "blocked_tags": [], "version": 0}
    )


def digest(payload, student_id, actor_id):
    return hashlib.sha256(
        (str(student_id) + actor_id + payload.model_dump_json()).encode()
    ).hexdigest()


def repeated(db, member, key, hash):
    e = db.scalar(scoped(m.WalletEntry, member).where(m.WalletEntry.key == str(key)))
    if e and e.payload_hash != hash:
        raise HTTPException(409, "Identificador da operação já usado com outros dados.")
    return e


@router.get("/inventory")
def products(
    channel: Literal["canteen", "store"] | None = None,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    permit(member, STAFF | {"guardian", "student"})
    stmt = scoped(m.InventoryItem, member)
    if member.role not in STAFF:
        stmt = stmt.where(m.InventoryItem.active.is_(True))
    if channel:
        stmt = stmt.where(m.InventoryItem.channel == channel)
    return [
        product_dto(p)
        for p in db.scalars(
            stmt.order_by(m.InventoryItem.name, m.InventoryItem.id)
            .offset(offset)
            .limit(limit)
        )
    ]


@router.post("/inventory", status_code=201)
def add_product(
    payload: ProductIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    return product_dto(create(db, m.InventoryItem, payload.model_dump(), member))


@router.put("/inventory/{item_id}")
def edit_product(
    item_id: UUID,
    payload: ProductChange,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    p = find(db, m.InventoryItem, item_id, member, lock=True)
    if p.version != payload.version:
        raise HTTPException(409, "Estoque alterado. Recarregue antes de atualizar.")
    if payload.channel != p.channel:
        raise HTTPException(
            422,
            "O canal de um produto não pode ser alterado. Cadastre outro produto no canal desejado.",
        )
    before = product_dto(p)
    for field, value in payload.model_dump(exclude={"version", "note"}).items():
        setattr(p, field, value)
    p.version += 1
    create(
        db,
        m.ServiceRecord,
        {
            "module": "inventory_change",
            "title": "Ajuste de catálogo/estoque",
            "owner_id": member.user_id,
            "data": {"before": before, "after": product_dto(p), "note": payload.note},
            "status": "recorded",
        },
        member,
    )
    return product_dto(p)


@router.get("/wallets/{student_id}")
def statement(
    student_id: UUID,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    student = wallet_access(db, member, student_id)
    entries = list(
        db.scalars(
            scoped(m.WalletEntry, member)
            .where(m.WalletEntry.student_id == str(student_id))
            .order_by(m.WalletEntry.created_at.desc(), m.WalletEntry.id)
            .offset(offset)
            .limit(limit)
        )
    )
    orders = {
        o.entry_id: o
        for o in db.scalars(
            scoped(m.StoreOrder, member).where(
                m.StoreOrder.entry_id.in_([e.id for e in entries])
            )
        )
    }
    refunds = set(
        db.scalars(
            scoped(m.WalletEntry, member)
            .with_only_columns(m.WalletEntry.reverses_id)
            .where(m.WalletEntry.reverses_id.in_([e.id for e in entries]))
        )
    )
    audit(db, member, "wallets.read", student.id)
    return {
        "student": student.name,
        "balance_cents": balance(db, member, student_id),
        "policy": policy(db, member, student_id),
        "entries": [
            {
                "id": e.id,
                "kind": e.kind,
                "channel": e.channel,
                "amount_cents": e.amount_cents,
                "note": e.note,
                "lines": e.lines,
                "created_at": e.created_at,
                "refunded": e.id in refunds,
                "order": {
                    "id": orders[e.id].id,
                    "status": orders[e.id].status,
                    "version": orders[e.id].version,
                }
                if e.id in orders
                else None,
            }
            for e in entries
        ],
    }


@router.put("/wallets/{student_id}/policy")
def set_policy(
    student_id: UUID,
    payload: PolicyIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF | {"guardian"})
    wallet_access(db, member, student_id, True)
    current = db.scalar(
        scoped(m.WalletPolicy, member).where(
            m.WalletPolicy.student_id == str(student_id)
        )
    )
    if (current.version if current else 0) != payload.version:
        raise HTTPException(409, "Limites alterados. Recarregue antes de salvar.")
    encrypted = cipher().encrypt(
        json.dumps(payload.model_dump(exclude={"version"})).encode()
    )
    if current:
        current.encrypted = encrypted
        current.version += 1
    else:
        create(
            db,
            m.WalletPolicy,
            {"student_id": str(student_id), "encrypted": encrypted},
            member,
        )
    audit(db, member, "wallets.policy", str(student_id))
    return {"message": "Limites e bloqueios atualizados."}


@router.post("/wallets/{student_id}/credit", status_code=201)
def credit(
    student_id: UUID,
    payload: CreditIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    wallet_access(db, member, student_id, True)
    hash = digest(payload, student_id, member.user_id)
    existing = repeated(db, member, payload.key, hash)
    if existing:
        return {
            "id": existing.id,
            "balance_cents": balance(db, member, student_id),
            "already_applied": True,
        }
    e = create(
        db,
        m.WalletEntry,
        {
            "student_id": str(student_id),
            "actor_id": member.user_id,
            "key": str(payload.key),
            "payload_hash": hash,
            "kind": "credit",
            "amount_cents": payload.amount_cents,
            "note": payload.note,
            "lines": [],
        },
        member,
    )
    return {
        "id": e.id,
        "balance_cents": balance(db, member, student_id),
        "already_applied": False,
    }


@router.post("/wallets/{student_id}/purchase", status_code=201)
def purchase(
    student_id: UUID,
    payload: PurchaseIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF | {"guardian"})
    wallet_access(db, member, student_id, True)
    if member.role == "guardian" and payload.channel != "store":
        raise HTTPException(403, "Consumos da cantina são registrados pela equipe.")
    hash = digest(payload, student_id, member.user_id)
    existing = repeated(db, member, payload.key, hash)
    if existing:
        return {
            "id": existing.id,
            "amount_cents": existing.amount_cents,
            "already_applied": True,
        }
    if len({line.product_id for line in payload.lines}) != len(payload.lines):
        raise HTTPException(422, "Produto repetido no pedido.")
    lines = []
    products = []
    restrictions = (
        policy(db, member, student_id) if payload.channel == "canteen" else None
    )
    for line in sorted(payload.lines, key=lambda l: str(l.product_id)):
        p = find(db, m.InventoryItem, line.product_id, member, lock=True)
        if p.version != line.version:
            raise HTTPException(
                409,
                "Catálogo alterado. Atualize os produtos antes de confirmar o pedido.",
            )
        if not p.active or p.channel != payload.channel or p.stock < line.quantity:
            raise HTTPException(409, "Produto indisponível ou estoque insuficiente.")
        if restrictions and set(p.tags) & set(restrictions["blocked_tags"]):
            raise HTTPException(
                409, "Produto bloqueado nas preferências alimentares do aluno."
            )
        products.append((p, line.quantity))
        lines.append(
            {
                "product_id": p.id,
                "name": p.name,
                "quantity": line.quantity,
                "unit_price_cents": p.price_cents,
            }
        )
    amount = sum(l["quantity"] * l["unit_price_cents"] for l in lines)
    if amount > 1000000000:
        raise HTTPException(422, "Valor do pedido excede o limite da operação.")
    if balance(db, member, student_id) < amount:
        raise HTTPException(409, "Saldo insuficiente na carteira.")
    if restrictions and restrictions["daily_limit_cents"] is not None:
        zone = ZoneInfo("America/Sao_Paulo")
        today = datetime.now(zone).date()
        start = datetime.combine(today, time(), zone)
        end = datetime.combine(today + timedelta(days=1), time(), zone)
        debits = list(
            db.scalars(
                scoped(m.WalletEntry, member).where(
                    m.WalletEntry.student_id == str(student_id),
                    m.WalletEntry.kind == "debit",
                    m.WalletEntry.channel == "canteen",
                    m.WalletEntry.created_at >= start,
                    m.WalletEntry.created_at < end,
                )
            )
        )
        refunds = db.scalar(
            scoped(m.WalletEntry, member)
            .with_only_columns(func.coalesce(func.sum(m.WalletEntry.amount_cents), 0))
            .where(
                m.WalletEntry.kind == "refund",
                m.WalletEntry.reverses_id.in_([d.id for d in debits]),
            )
        )
        if (
            sum(d.amount_cents for d in debits) - refunds + amount
            > restrictions["daily_limit_cents"]
        ):
            raise HTTPException(409, "O consumo ultrapassa o limite diário da cantina.")
    for p, quantity in products:
        p.stock -= quantity
        p.version += 1
    e = create(
        db,
        m.WalletEntry,
        {
            "student_id": str(student_id),
            "actor_id": member.user_id,
            "key": str(payload.key),
            "payload_hash": hash,
            "kind": "debit",
            "channel": payload.channel,
            "amount_cents": amount,
            "note": "Consumo da cantina"
            if payload.channel == "canteen"
            else "Pedido na loja escolar",
            "lines": lines,
        },
        member,
    )
    if payload.channel == "store":
        create(db, m.StoreOrder, {"entry_id": e.id}, member)
    return {"id": e.id, "amount_cents": amount, "already_applied": False}


@router.post("/wallet-entries/{item_id}/refund", status_code=201)
def refund(
    item_id: UUID,
    payload: RefundIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    original = find(db, m.WalletEntry, item_id, member)
    wallet_access(db, member, original.student_id, True)
    hash = digest(payload, original.student_id, member.user_id)
    existing = repeated(db, member, payload.key, hash)
    if existing:
        if existing.reverses_id != original.id:
            raise HTTPException(409, "Identificador usado por outro estorno.")
        return {"id": existing.id, "already_applied": True}
    if original.kind != "debit" or db.scalar(
        scoped(m.WalletEntry, member).where(m.WalletEntry.reverses_id == original.id)
    ):
        raise HTTPException(409, "Operação não pode ser estornada novamente.")
    if payload.restock:
        for line in sorted(original.lines, key=lambda l: l["product_id"]):
            p = find(db, m.InventoryItem, line["product_id"], member, lock=True)
            if p.stock + line["quantity"] > 1000000:
                raise HTTPException(422, "Reposição excede o limite de estoque.")
            p.stock += line["quantity"]
            p.version += 1
    e = create(
        db,
        m.WalletEntry,
        {
            "student_id": original.student_id,
            "actor_id": member.user_id,
            "key": str(payload.key),
            "payload_hash": hash,
            "kind": "refund",
            "channel": original.channel,
            "amount_cents": original.amount_cents,
            "note": payload.note,
            "lines": original.lines,
            "reverses_id": original.id,
        },
        member,
    )
    order = db.scalar(
        scoped(m.StoreOrder, member).where(m.StoreOrder.entry_id == original.id)
    )
    if order:
        order.status = "cancelled"
        order.version += 1
    return {"id": e.id, "already_applied": False}


@router.post("/store-orders/{item_id}/deliver")
def deliver(
    item_id: UUID,
    payload: DeliveryIn,
    member=Depends(membership),
    db: Session = Depends(database, scope="function"),
):
    permit(member, STAFF)
    order = find(db, m.StoreOrder, item_id, member)
    entry = find(db, m.WalletEntry, order.entry_id, member)
    wallet_access(db, member, entry.student_id, True)
    order = find(db, m.StoreOrder, item_id, member, lock=True)
    if order.status != "placed" or order.version != payload.version:
        raise HTTPException(409, "Pedido já alterado, entregue ou cancelado.")
    order.status = "delivered"
    order.version += 1
    create(
        db,
        m.ServiceRecord,
        {
            "module": "store_delivery",
            "title": "Entrega de pedido",
            "student_id": entry.student_id,
            "owner_id": member.user_id,
            "data": {"order_id": order.id, "note": payload.note},
            "status": "delivered",
        },
        member,
    )
    return {"message": "Entrega registrada."}

import base64
import gzip
import json
from datetime import datetime, timedelta, timezone
import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.fernet import Fernet
from lxml import etree as E
from signxml import (
    XMLVerifier,
    SignatureConfiguration,
    SignatureMethod,
    DigestAlgorithm,
)
from sqlalchemy.orm import Session
from uuid import uuid4
from app import models as m, nfse_national as national
from app.db import engine, tenant_context
from conftest import authenticate


@pytest.fixture
def fiscal(client, context, monkeypatch):
    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    h, b = context
    profile = {
        "version": 0,
        "cnpj": "11222333000181",
        "legal_name": "Escola Fiscal Sintética",
        "municipality_code": "3304904",
        "municipal_registration": "",
        "environment": "test",
        "series": 1,
        "next_number": 1,
        "service_code": "080101",
        "municipal_service_code": "",
        "nbs_code": "",
        "simple_national": 3,
        "simple_apportionment": 1,
        "special_regime": 0,
        "total_tax_percent": "6.00",
        "federal_tax_percent": "0",
        "state_tax_percent": "0",
        "municipal_tax_percent": "0",
        "accounting_confirmed": True,
    }
    response = client.put(b + "/fiscal/profile", headers=h, json=profile)
    assert response.status_code == 200, response.text
    guardian = next(
        g
        for g in client.get(b + "/guardians", headers=h).json()
        if g["email"] == "familia@aurora.example.com"
    )
    sid = next(
        l["student_id"]
        for l in client.get(b + "/guardian-links", headers=h).json()
        if l["guardian_id"] == guardian["id"]
    )
    data = {
        "key": str(uuid4()),
        "profile_version": 1,
        "student_id": sid,
        "guardian_id": guardian["id"],
        "tax_id": "52998224725",
        "competence": datetime.now(timezone.utc).date().isoformat(),
        "amount_cents": 65000,
        "description": "Mensalidade de demonstração, sem serviço real",
        "postal_code": "24452000",
        "municipality_code": "3304904",
        "street": "Rua de demonstração",
        "street_number": "100",
        "district": "Engenho Pequeno",
    }
    r = client.post(b + "/fiscal/invoices", headers=h, json=data)
    assert r.status_code == 201, r.text
    return h, b, profile, data, r.json()


@pytest.fixture
def signing():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TESTE 11222333000181")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM), key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def provider_reply(dps, cert, key):
    ns = national.NS
    root = E.Element("{" + ns + "}NFSe", nsmap={None: ns}, versao="1.01")

    def node(parent, name, value=None):
        e = E.SubElement(parent, "{" + ns + "}" + name)
        if value is not None:
            e.text = str(value)
        return e

    access_key = "3" * 50
    inf = node(root, "infNFSe")
    inf.set("Id", "NFS" + access_key)
    for name, value in [
        ("xLocEmi", "São Gonçalo"),
        ("xLocPrestacao", "São Gonçalo"),
        ("nNFSe", "1"),
        ("xTribNac", "Ensino de demonstração"),
        ("verAplic", "TESTE"),
        ("ambGer", "2"),
        ("tpEmis", "1"),
        ("cStat", "100"),
        ("dhProc", datetime.now(timezone.utc).replace(microsecond=0).isoformat()),
        ("nDFSe", "1"),
    ]:
        node(inf, name, value)
    emit = node(inf, "emit")
    node(emit, "CNPJ", "11222333000181")
    node(emit, "xNome", "Escola Fiscal Sintética")
    end = node(emit, "enderNac")
    # Order follows the official national XSD.
    for name, value in [
        ("xLgr", "Rua Sintética"),
        ("nro", "100"),
        ("xBairro", "Engenho Pequeno"),
        ("cMun", "3304904"),
        ("UF", "RJ"),
        ("CEP", "24452000"),
    ]:
        node(end, name, value)
    values = node(inf, "valores")
    node(values, "vLiq", "650.00")
    inf.append(E.fromstring(dps, parser=national.PARSER()))
    signed = national.NationalSigner(
        signature_algorithm="rsa-sha1",
        digest_algorithm="sha1",
        c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    ).sign(
        root, key=key, cert=cert, reference_uri="#NFS" + access_key, id_attribute="Id"
    )
    xml = E.tostring(signed, xml_declaration=True, encoding="UTF-8")
    national.validate(xml, "NFSe_v1.01.xsd")
    return httpx.Response(
        201,
        json={
            "chaveAcesso": access_key,
            "nfseXmlGZipB64": base64.b64encode(gzip.compress(xml)).decode(),
        },
    )


def test_fiscal_draft_idempotency_encryption_sequence_and_permissions(client, fiscal):
    h, b, profile, data, r = fiscal
    repeat = client.post(b + "/fiscal/invoices", headers=h, json=data)
    assert repeat.json()["id"] == r["id"]
    assert client.get(b + "/fiscal/profile", headers=h).json()["next_number"] == 2
    assert (
        client.post(
            b + "/fiscal/invoices", headers=h, json={**data, "amount_cents": 70000}
        ).status_code
        == 409
    )
    assert (
        client.put(
            b + "/fiscal/profile",
            headers=h,
            json={**profile, "version": 2, "next_number": 1},
        ).status_code
        == 409
    )
    assert (
        client.get(b + "/fiscal/invoices/" + r["id"] + "/xml", headers=h).status_code
        == 409
    )
    for role in ["guardian", "student", "teacher", "coordinator", "psychologist"]:
        other = authenticate(client, role + "@aurora.example.com")
        assert client.get(b + "/fiscal/invoices", headers=other).status_code == 403
        assert client.get(b + "/fiscal/profile", headers=other).status_code == 403
    secretary = authenticate(client, "secretary@aurora.example.com")
    assert (
        client.put(b + "/fiscal/profile", headers=secretary, json=profile).status_code
        == 403
    )
    assert client.get(b + "/fiscal/invoices", headers=secretary).status_code == 200
    with Session(engine) as db, db.begin():
        tenant_context(db, b.rsplit("/", 1)[1])
        row = db.get(m.FiscalInvoice, r["id"])
        assert b"52998224725" not in row.encrypted
        xml = national.build_dps(
            row,
            json.loads(
                Fernet(__import__("os").environ["APP_ENCRYPTION_KEY"].encode()).decrypt(
                    row.encrypted
                )
            ),
        )
        assert b"650.00" in xml and row.dps_id.encode() in xml


def test_fiscal_missing_certificate_does_not_simulate_authorization(
    client, fiscal, monkeypatch
):
    h, b, _, _, r = fiscal
    monkeypatch.delenv("NFSE_CERTIFICATES_FILE", raising=False)
    response = client.post(
        b + "/fiscal/invoices/" + r["id"] + "/emit", headers=h, json={"version": 1}
    )
    assert response.status_code == 409
    record = client.get(b + "/fiscal/invoices", headers=h).json()[0]
    assert record["status"] == "draft" and record["access_key"] is None


def test_national_signature_durable_send_and_authorized_xml(
    client, fiscal, signing, monkeypatch
):
    h, b, _, _, r = fiscal
    cert, key = signing
    monkeypatch.setattr(national, "credentials", lambda *a: (cert, key, None))
    calls = []

    def send(env, ctx, method, path, xml=None):
        assert env == "test" and path == "/nfse" and method == "POST"
        # Provider call occurs after the signed DPS/status have been committed.
        with Session(engine) as db, db.begin():
            tenant_context(db, b.rsplit("/", 1)[1])
            row = db.get(m.FiscalInvoice, r["id"])
            assert row.status == "submitting" and row.signed_xml is not None
        cfg = SignatureConfiguration(
            signature_methods=frozenset({SignatureMethod.RSA_SHA1}),
            digest_algorithms=frozenset({DigestAlgorithm.SHA1}),
        )
        verified = (
            XMLVerifier()
            .verify(xml, x509_cert=cert, expect_config=cfg, id_attribute="Id")
            .signed_xml
        )
        assert verified.get("Id") == r["dps_id"]
        calls.append(xml)
        return provider_reply(xml, cert, key)

    monkeypatch.setattr(national, "request", send)
    result = client.post(
        b + "/fiscal/invoices/" + r["id"] + "/emit", headers=h, json={"version": 1}
    )
    assert result.status_code == 200, result.text
    assert (
        result.json()["status"] == "authorized"
        and "Sem validade fiscal" in result.json()["message"]
    )
    repeat = client.post(
        b + "/fiscal/invoices/" + r["id"] + "/emit", headers=h, json={"version": 1}
    )
    assert repeat.json()["status"] == "authorized" and len(calls) == 1
    download = client.get(b + "/fiscal/invoices/" + r["id"] + "/xml", headers=h)
    assert download.status_code == 200 and download.json()["filename"].startswith(
        "HOMOLOGACAO-"
    )
    national.validate(base64.b64decode(download.json()["base64"]), "NFSe_v1.01.xsd")


def test_timeout_requires_dps_query_and_never_creates_another_number(
    client, fiscal, signing, monkeypatch
):
    h, b, _, _, r = fiscal
    cert, key = signing
    monkeypatch.setattr(national, "credentials", lambda *a: (cert, key, None))

    def timeout(*a, **kw):
        raise httpx.ReadTimeout("simulação")

    monkeypatch.setattr(national, "request", timeout)
    first = client.post(
        b + "/fiscal/invoices/" + r["id"] + "/emit", headers=h, json={"version": 1}
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "unknown"
    assert (
        client.post(
            b + "/fiscal/invoices/" + r["id"] + "/emit",
            headers=h,
            json={"version": first.json()["version"]},
        ).status_code
        == 409
    )
    calls = []

    def query(env, ctx, method, path, xml=None):
        calls.append(path)
        if path.startswith("/dps/"):
            return httpx.Response(
                200,
                json={"chaveAcesso": "3" * 50},
                request=httpx.Request("GET", "https://example.invalid"),
            )
        with Session(engine) as db, db.begin():
            tenant_context(db, b.rsplit("/", 1)[1])
            row = db.get(m.FiscalInvoice, r["id"])
            dps = Fernet(
                __import__("os").environ["APP_ENCRYPTION_KEY"].encode()
            ).decrypt(row.signed_xml)
        return provider_reply(dps, cert, key)

    monkeypatch.setattr(national, "request", query)
    confirmed = client.post(
        b + "/fiscal/invoices/" + r["id"] + "/reconcile",
        headers=h,
        json={"version": first.json()["version"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert (
        confirmed.json()["status"] == "authorized" and calls[0] == "/dps/" + r["dps_id"]
    )
    assert client.get(b + "/fiscal/profile", headers=h).json()["next_number"] == 2


def test_fiscal_refuses_invalid_tax_id_and_unverified_tomador(client, fiscal):
    h, b, _, data, r = fiscal
    assert (
        client.post(
            b + "/fiscal/invoices",
            headers=h,
            json={**data, "key": str(uuid4()), "tax_id": "11111111111"},
        ).status_code
        == 422
    )
    link = next(
        l
        for l in client.get(b + "/guardian-links", headers=h).json()
        if l["student_id"] == data["student_id"]
    )
    assert (
        client.delete(b + "/guardian-links/" + link["id"], headers=h).status_code == 204
    )
    assert (
        client.post(
            b + "/fiscal/invoices",
            headers=h,
            json={**data, "key": str(uuid4()), "profile_version": 2},
        ).status_code
        == 422
    )
    other = authenticate(client, "director@horizonte.example.com")
    base = (
        "/api/v1/institutions/"
        + client.get("/api/v1/me", headers=other).json()["memberships"][0][
            "institution_id"
        ]
    )
    assert (
        client.get(
            base + "/fiscal/invoices/" + r["id"] + "/xml", headers=other
        ).status_code
        == 404
    )


def test_certificate_binding_and_production_activation(
    client, fiscal, signing, monkeypatch, tmp_path
):
    h, b, _, _, _ = fiscal
    cert, key = signing
    cert_file = tmp_path / "cert.pem"
    cert_file.write_bytes(cert)
    key_file = tmp_path / "key.pem"
    key_file.write_bytes(key)
    school_id = client.get("/api/v1/me", headers=h).json()["memberships"][0][
        "school_id"
    ]
    config_file = tmp_path / "certificates.json"
    config = {
        school_id: {
            "cnpj": "11222333000181",
            "certificate": str(cert_file),
            "private_key": str(key_file),
            "production_enabled": False,
        }
    }
    config_file.write_text(json.dumps(config))
    monkeypatch.setenv("NFSE_CERTIFICATES_FILE", str(config_file))
    assert national.credentials(school_id, "11222333000181", "test")[0] == cert
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        national.credentials(school_id, "11222333000181", "production")
    with pytest.raises(HTTPException):
        national.credentials(school_id, "11444777000161", "test")


@pytest.mark.parametrize("mismatch", ["key", "payload"])
def test_invalid_official_response_never_marks_authorized(
    client, fiscal, signing, monkeypatch, mismatch
):
    h, b, _, _, r = fiscal
    cert, key = signing
    monkeypatch.setattr(national, "credentials", lambda *args: (cert, key, None))

    def wrong_response(env, context, method, path, xml=None):
        if mismatch == "payload":
            changed = E.fromstring(xml, parser=national.PARSER())
            changed.remove(
                changed.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
            )
            changed.find(".//{" + national.NS + "}vServ").text = "999.00"
            xml = national.sign_dps(E.tostring(changed), cert, key)
        result = provider_reply(xml, cert, key).json()
        if mismatch == "key":
            result["chaveAcesso"] = "4" * 50
        return httpx.Response(201, json=result)

    monkeypatch.setattr(national, "request", wrong_response)
    result = client.post(
        b + "/fiscal/invoices/" + r["id"] + "/emit", headers=h, json={"version": 1}
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "unknown" and result.json()["access_key"] is None
    assert (
        client.get(b + "/fiscal/invoices/" + r["id"] + "/xml", headers=h).status_code
        == 409
    )


@pytest.mark.parametrize(
    "changes", [{"simple_national": 1}, {"simple_national": 2}, {"special_regime": 9}]
)
def test_fiscal_blocks_tax_regimes_outside_initial_scope(client, fiscal, changes):
    h, b, profile, _, _ = fiscal
    attempted = client.put(
        b + "/fiscal/profile",
        headers=h,
        json={**profile, "version": 2, "next_number": 2, **changes},
    )
    assert attempted.status_code == 422
    assert client.get(b + "/fiscal/profile", headers=h).json()["simple_national"] == 3

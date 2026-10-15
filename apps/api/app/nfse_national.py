"""National NFS-e adapter. No production call without an explicit per-school certificate binding."""

import base64
import gzip
import io
import json
import os
import re
import ssl
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import httpx
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from lxml import etree as E
from signxml import XMLSigner

NS = "http://www.sped.fazenda.gov.br/nfse"
ASSETS = Path(__file__).parent / "assets" / "nfse"
ENDPOINTS = {
    "test": "https://sefin.producaorestrita.nfse.gov.br/API/SefinNacional",
    "production": "https://sefin.nfse.gov.br/SefinNacional",
}
PARSER = lambda: E.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)


def validate(xml, name):
    if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
        raise ValueError("DTD is forbidden")
    root = E.fromstring(xml, parser=PARSER())

    # The published series facet contains PCRE anchors, which XSD 1.0 treats as
    # literal characters. Normalize that single known facet to its intended
    # numeric restriction, without disabling any other official validation.
    class SchemaResolver(E.Resolver):
        def resolve(self, url, public_id, context):
            if url.endswith("tiposSimples_v1.01.xsd"):
                data = (ASSETS / "tiposSimples_v1.01.xsd").read_bytes()
                data = data.replace(
                    b'value="^0{0,4}\\d{1,5}$"', b'value="0{0,4}[0-9]{1,5}"'
                )
                return self.resolve_string(data, context)

    parser = PARSER()
    parser.resolvers.add(SchemaResolver())
    E.XMLSchema(E.parse(str(ASSETS / name), parser=parser)).assertValid(root)
    return root


def build_dps(invoice, content, emitted=None):
    profile = content["profile"]
    if (
        profile["simple_national"] != 3
        or profile["simple_apportionment"] != 1
        or profile["special_regime"] != 0
    ):
        raise ValueError("Tax regime not supported by this emission flow")
    doc = content["request"]
    root = E.Element("{" + NS + "}DPS", nsmap={None: NS}, versao="1.01")

    def node(parent, name, text=None):
        child = E.SubElement(parent, "{" + NS + "}" + name)
        if text is not None:
            child.text = str(text)
        return child

    inf = node(root, "infDPS")
    inf.set("Id", invoice.dps_id)
    for name, value in [
        ("tpAmb", 2 if invoice.environment == "test" else 1),
        (
            "dhEmi",
            (emitted or datetime.now(timezone.utc)).replace(microsecond=0).isoformat(),
        ),
        ("verAplic", "SIESCO-1.0"),
        ("serie", invoice.series),
        ("nDPS", invoice.number),
        ("dCompet", doc["competence"]),
        ("tpEmit", 1),
        ("cLocEmi", profile["municipality_code"]),
    ]:
        node(inf, name, value)
    prest = node(inf, "prest")
    node(prest, "CNPJ", profile["cnpj"])
    if profile["municipal_registration"]:
        node(prest, "IM", profile["municipal_registration"])
    node(prest, "xNome", profile["legal_name"])
    regime = node(prest, "regTrib")
    node(regime, "opSimpNac", profile["simple_national"])
    if profile["simple_national"] == 3:
        node(regime, "regApTribSN", profile["simple_apportionment"])
    node(regime, "regEspTrib", profile["special_regime"])
    toma = node(inf, "toma")
    node(toma, "CPF" if len(doc["tax_id"]) == 11 else "CNPJ", doc["tax_id"])
    node(toma, "xNome", content["guardian"])
    address = node(toma, "end")
    national = node(address, "endNac")
    node(national, "cMun", doc["municipality_code"])
    node(national, "CEP", doc["postal_code"])
    for name, key in [
        ("xLgr", "street"),
        ("nro", "street_number"),
        ("xBairro", "district"),
    ]:
        node(address, name, doc[key])
    service = node(inf, "serv")
    location = node(service, "locPrest")
    node(location, "cLocPrestacao", profile["municipality_code"])
    code = node(service, "cServ")
    node(code, "cTribNac", profile["service_code"])
    if profile["municipal_service_code"]:
        node(code, "cTribMun", profile["municipal_service_code"])
    node(code, "xDescServ", doc["description"])
    if profile["nbs_code"]:
        node(code, "cNBS", profile["nbs_code"])
    values = node(inf, "valores")
    payment = node(values, "vServPrest")
    node(payment, "vServ", format(Decimal(doc["amount_cents"]) / 100, ".2f"))
    taxes = node(values, "trib")
    municipal = node(taxes, "tribMun")
    node(municipal, "tribISSQN", 1)
    node(municipal, "tpRetISSQN", 1)
    total = node(taxes, "totTrib")
    if profile["simple_national"] == 3:
        node(total, "pTotTribSN", profile["total_tax_percent"])
    else:
        percentages = node(total, "pTotTrib")
        for key in ["federal", "state", "municipal"]:
            node(
                percentages,
                {
                    "federal": "pTotTribFed",
                    "state": "pTotTribEst",
                    "municipal": "pTotTribMun",
                }[key],
                profile[key + "_tax_percent"],
            )
    xml = E.tostring(root, xml_declaration=True, encoding="UTF-8")
    validate(xml, "DPS_v1.01.xsd")
    return xml


def credentials(school_id, cnpj, environment):
    try:
        settings = json.loads(Path(os.environ["NFSE_CERTIFICATES_FILE"]).read_text())
        config = settings[school_id]
        if config["cnpj"] != cnpj or (
            environment == "production" and config.get("production_enabled") is not True
        ):
            raise ValueError("Not enabled")
        cert = Path(config["certificate"]).read_bytes()
        key = Path(config["private_key"]).read_bytes()
        leaf = x509.load_pem_x509_certificate(cert)
        private = serialization.load_pem_private_key(key, password=None)
        if (
            not isinstance(private, rsa.RSAPrivateKey)
            or private.public_key().public_numbers()
            != leaf.public_key().public_numbers()
        ):
            raise ValueError("Key mismatch")
        now = datetime.now(timezone.utc)
        if not leaf.not_valid_before_utc <= now <= leaf.not_valid_after_utc:
            raise ValueError("Expired certificate")
        identifiers = []
        for value in leaf.subject:
            identifiers.extend(re.findall(r"\d{14}", value.value))
        try:
            for name in leaf.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value:
                if (
                    isinstance(name, x509.OtherName)
                    and name.type_id.dotted_string == "2.16.76.1.3.3"
                ):
                    identifiers.extend(re.findall(rb"\d{14}", name.value))
        except x509.ExtensionNotFound:
            pass
        if not any(
            (v.decode() if isinstance(v, bytes) else v)[:8] == cnpj[:8]
            for v in identifiers
        ):
            raise ValueError("CNPJ mismatch")
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(config["certificate"], config["private_key"])
        return cert, key, context
    except (KeyError, ValueError, OSError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            409,
            "Certificado fiscal não configurado, inválido ou não liberado para este CNPJ/ambiente. A direção deve concluir a configuração segura com o contador.",
        )


class NationalSigner(XMLSigner):
    # SHA-1 is confined to the government XMLDSig protocol; never used for application hashes.
    def check_deprecated_methods(self):
        pass


def sign_dps(xml, cert, key):
    root = E.fromstring(xml, parser=PARSER())
    identifier = root[0].get("Id")
    signer = NationalSigner(
        signature_algorithm="rsa-sha1",
        digest_algorithm="sha1",
        c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
    )
    signed = signer.sign(
        root, key=key, cert=cert, reference_uri="#" + identifier, id_attribute="Id"
    )
    result = E.tostring(signed, xml_declaration=True, encoding="UTF-8")
    validate(result, "DPS_v1.01.xsd")
    return result


def request(environment, context, method, path, xml=None):
    with httpx.Client(
        verify=context,
        timeout=httpx.Timeout(30, connect=5),
        follow_redirects=False,
        trust_env=False,
    ) as client:
        return client.request(
            method,
            ENDPOINTS[environment] + path,
            json={
                "dpsXmlGZipB64": base64.b64encode(gzip.compress(xml, mtime=0)).decode()
            }
            if xml is not None
            else None,
        )


def authorized_result(response, invoice, signed_xml):
    body = response.json()
    if response.status_code not in (200, 201) or body.get("erros"):
        return None
    key = body["chaveAcesso"]
    if not re.fullmatch(r"[0-9]{50}", key):
        raise ValueError("Invalid access key")
    compressed = base64.b64decode(body["nfseXmlGZipB64"], validate=True)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        xml = stream.read(2 * 1024 * 1024 + 1)
    if len(xml) > 2 * 1024 * 1024:
        raise ValueError("Oversized XML")
    root = validate(xml, "NFSe_v1.01.xsd")
    info = root.find("{" + NS + "}infNFSe")
    dps = info.find("{" + NS + "}DPS/{" + NS + "}infDPS")
    if info.get("Id") != "NFS" + key or dps is None or dps.get("Id") != invoice.dps_id:
        raise ValueError("Unrelated fiscal response")
    if dps.findtext(
        "{" + NS + "}prest/{" + NS + "}CNPJ"
    ) != invoice.cnpj or dps.findtext("{" + NS + "}tpAmb") != (
        "2" if invoice.environment == "test" else "1"
    ):
        raise ValueError("Fiscal emitter/environment mismatch")
    expected = E.fromstring(signed_xml, parser=PARSER()).find("{" + NS + "}infDPS")
    if expected is None or E.tostring(dps, method="c14n", exclusive=True) != E.tostring(
        expected, method="c14n", exclusive=True
    ):
        raise ValueError(
            "Returned DPS differs from the declaration signed by this platform"
        )
    return key, xml

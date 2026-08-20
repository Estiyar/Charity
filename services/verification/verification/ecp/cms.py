import base64
import hashlib

from asn1crypto import cms as asn1_cms
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.x509 import load_der_x509_certificate

from .exceptions import EcpVerificationError

GOST_OID_PREFIXES = ("1.2.398.", "1.2.156.10197.")

DIGEST_MAP = {
    "sha1": hashes.SHA1(),
    "sha256": hashes.SHA256(),
    "sha384": hashes.SHA384(),
    "sha512": hashes.SHA512(),
}


def load_cms_der(raw_cms):
    if isinstance(raw_cms, bytes) and raw_cms[:1] == b"\x30":
        return raw_cms
    text = raw_cms.decode("utf-8") if isinstance(raw_cms, bytes) else str(raw_cms)
    stripped = text.strip()
    if stripped.startswith("-----BEGIN"):
        body = "".join(line for line in stripped.splitlines() if not line.startswith("-----"))
        return base64.b64decode(body)
    try:
        return base64.b64decode(stripped, validate=True)
    except Exception:
        return base64.b64decode(stripped)


def algorithm_oid(algorithm):
    dotted = getattr(algorithm, "dotted", None)
    if dotted:
        return dotted
    native = algorithm.native if hasattr(algorithm, "native") else str(algorithm)
    return str(native)


def is_gost_algorithm(algorithm):
    oid = algorithm_oid(algorithm)
    return oid.startswith(GOST_OID_PREFIXES)


def _certificate_from_choice(cert_choice):
    name = getattr(cert_choice, "name", None)
    if name not in (None, "certificate"):
        return None
    chosen = cert_choice.chosen if hasattr(cert_choice, "chosen") else cert_choice
    for candidate in (chosen, cert_choice):
        dump = getattr(candidate, "dump", None)
        if dump is None:
            continue
        try:
            return load_der_x509_certificate(dump())
        except Exception:
            continue
    return None


def _public_key_from_signer(signed_data, signer_info):
    sid = signer_info["sid"]
    serial = None
    if sid.name == "issuer_and_serial_number":
        serial = sid.chosen["serial_number"].native
    for cert_choice in signed_data["certificates"] or []:
        certificate = _certificate_from_choice(cert_choice)
        if certificate is None:
            continue
        if serial is None or certificate.serial_number == serial:
            return certificate
    raise EcpVerificationError("В CMS нет сертификата подписанта.")


def _signed_attrs_for_verify(signed_attrs):
    encoded = signed_attrs.dump()
    if encoded and encoded[0] == 0xA0:
        return b"\x31" + encoded[1:]
    return encoded


def _signed_payload(signer_info, encapsulated):
    signed_attrs = signer_info["signed_attrs"]
    if signed_attrs:
        digest_attr = None
        for attr in signed_attrs:
            if attr["type"].native == "message_digest":
                digest_attr = attr["values"][0].native
        if digest_attr is None:
            raise EcpVerificationError("В CMS нет messageDigest.")
        digest_name = signer_info["digest_algorithm"]["algorithm"].native
        if not isinstance(digest_name, str):
            digest_name = algorithm_oid(signer_info["digest_algorithm"]["algorithm"])
        digest = DIGEST_MAP.get(digest_name)
        if digest is None:
            raise EcpVerificationError("Алгоритм хеширования CMS не поддерживается локально.")
        hasher = hashes.Hash(digest)
        hasher.update(encapsulated)
        if hasher.finalize() != digest_attr:
            raise EcpVerificationError("Содержимое CMS не совпадает с подписью.")
        return _signed_attrs_for_verify(signed_attrs)
    return encapsulated


def resolve_digest(signer_info, signature_algorithm):
    name = signer_info["digest_algorithm"]["algorithm"].native
    if name in DIGEST_MAP:
        return DIGEST_MAP[name]
    signature_name = str(signature_algorithm["algorithm"].native)
    for key, algorithm in DIGEST_MAP.items():
        if key in signature_name:
            return algorithm
    return hashes.SHA256()


def verify_rsa_or_ecdsa(certificate, signature, payload, digest):
    public_key = certificate.public_key()
    try:
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(signature, payload, padding.PKCS1v15(), digest)
            return
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(signature, payload, ec.ECDSA(digest))
            return
    except Exception as exc:
        raise EcpVerificationError("Криптографическая проверка подписи не пройдена.") from exc
    raise EcpVerificationError("Тип ключа сертификата не поддерживается без внешнего верификатора.")


def parse_and_verify_cms(raw_cms, expected_payload):
    cms_der = load_cms_der(raw_cms)
    try:
        content_info = asn1_cms.ContentInfo.load(cms_der)
    except Exception as exc:
        raise EcpVerificationError("CMS-подпись повреждена или имеет неизвестный формат.") from exc
    if content_info["content_type"].native != "signed_data":
        raise EcpVerificationError("Ожидалась CMS SignedData подпись.")
    signed_data = content_info["content"]
    encapsulated = signed_data["encap_content_info"]["content"].native or b""
    if expected_payload and encapsulated and encapsulated != expected_payload:
        raise EcpVerificationError("Подпись относится к другому challenge.")
    if not signed_data["signer_infos"]:
        raise EcpVerificationError("В CMS нет подписанта.")
    signer_info = signed_data["signer_infos"][0]
    certificate = _public_key_from_signer(signed_data, signer_info)
    signature_algorithm = signer_info["signature_algorithm"]
    digest_algorithm = signer_info["digest_algorithm"]
    gost = is_gost_algorithm(signature_algorithm["algorithm"]) or is_gost_algorithm(
        digest_algorithm["algorithm"]
    )
    signature = signer_info["signature"].native
    payload = _signed_payload(signer_info, encapsulated or expected_payload)
    digest = None if gost else resolve_digest(signer_info, signature_algorithm)
    return {
        "cms_der": cms_der,
        "certificate": certificate,
        "encapsulated": encapsulated,
        "gost": gost,
        "signature": signature,
        "payload": payload,
        "digest": digest,
        "cms_hash": hashlib.sha256(cms_der).hexdigest(),
    }

from datetime import date

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import ExtensionOID, NameOID

from django.core.exceptions import ValidationError as DjangoValidationError

from ekomek_common.validators import validate_iin

NCA_IIN_PREFIX = "IIN"
NCA_BIN_PREFIX = "BIN"

CERTIFICATE_TYPE_INDIVIDUAL = "individual"
CERTIFICATE_TYPE_LEGAL = "legal"
CERTIFICATE_TYPE_CEO = "ceo"
CERTIFICATE_TYPE_EMPLOYEE = "employee"

NCA_POLICY_OIDS = {
    "1.2.398.3.3.4.1.1": CERTIFICATE_TYPE_INDIVIDUAL,
    "1.2.398.3.3.4.1.2": CERTIFICATE_TYPE_LEGAL,
    "1.2.398.3.3.4.1.2.1": CERTIFICATE_TYPE_CEO,
    "1.2.398.3.3.4.1.2.2": CERTIFICATE_TYPE_EMPLOYEE,
}

NCA_ISSUER_MARKERS = (
    "ҰЛТТЫҚ КУӘЛАНДЫРУШЫ ОРТАЛЫҚ",
    "НАЦИОНАЛЬНЫЙ УДОСТОВЕРЯЮЩИЙ ЦЕНТР",
    "NATIONAL CERTIFICATION AUTHORITY",
    "NCA OF REPUBLIC OF KAZAKHSTAN",
    "NCA RK",
    "ҰКО",
    "НУЦ",
)


def _name_value(name, oid_name):
    attributes = name.get_attributes_for_oid(oid_name)
    if not attributes:
        return ""
    return attributes[0].value


def extract_iin(certificate):
    serial = _name_value(certificate.subject, NameOID.SERIAL_NUMBER).strip()
    if serial.upper().startswith(NCA_IIN_PREFIX):
        candidate = serial[len(NCA_IIN_PREFIX) :]
    else:
        candidate = "".join(character for character in serial if character.isdigit())
    try:
        validate_iin(candidate)
    except DjangoValidationError as exc:
        from .exceptions import EcpVerificationError

        raise EcpVerificationError(exc.messages[0], code="invalid_iin") from exc
    return candidate


def extract_full_name(certificate):
    common_name = _name_value(certificate.subject, NameOID.COMMON_NAME).strip()
    surname = _name_value(certificate.subject, NameOID.SURNAME).strip()
    given = _name_value(certificate.subject, NameOID.GIVEN_NAME).strip()
    if surname and given:
        return f"{surname} {given}".strip()
    return common_name


def birth_date_from_iin(iin):
    year = int(iin[0:2])
    month = int(iin[2:4])
    day = int(iin[4:6])
    century_code = int(iin[6])
    if century_code in (1, 2):
        year += 1800
    elif century_code in (3, 4):
        year += 1900
    elif century_code in (5, 6):
        year += 2000
    else:
        year += 1900 if year >= 30 else 2000
    return date(year, month, day)


def extract_certificate_type(certificate):
    try:
        policies = certificate.extensions.get_extension_for_oid(ExtensionOID.CERTIFICATE_POLICIES)
        for policy in policies.value:
            mapped = NCA_POLICY_OIDS.get(policy.policy_identifier.dotted_string)
            if mapped:
                return mapped
    except Exception:
        pass
    serial = _name_value(certificate.subject, NameOID.SERIAL_NUMBER).upper()
    if serial.startswith(NCA_BIN_PREFIX):
        return CERTIFICATE_TYPE_LEGAL
    return CERTIFICATE_TYPE_INDIVIDUAL


def extract_issuer(certificate):
    return _name_value(certificate.issuer, NameOID.COMMON_NAME) or certificate.issuer.rfc4514_string()


def issuer_is_nca(certificate):
    issuer = extract_issuer(certificate).upper()
    return any(marker.upper() in issuer for marker in NCA_ISSUER_MARKERS)


def extract_certificate_fields(certificate):
    iin = extract_iin(certificate)
    return {
        "iin": iin,
        "full_name": extract_full_name(certificate),
        "birth_date": birth_date_from_iin(iin).isoformat(),
        "certificate_type": extract_certificate_type(certificate),
        "serial_number": format(certificate.serial_number, "x"),
        "issuer": extract_issuer(certificate),
        "valid_from": certificate.not_valid_before_utc.isoformat(),
        "valid_to": certificate.not_valid_after_utc.isoformat(),
        "fingerprint": certificate.fingerprint(hashes.SHA256()).hex(),
        "certificate_der": certificate.public_bytes(Encoding.DER),
    }

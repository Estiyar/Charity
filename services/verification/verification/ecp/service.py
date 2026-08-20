from datetime import date, datetime

from django.utils.dateparse import parse_date, parse_datetime

from ekomek_common.audit import reveal_encrypted
from ekomek_common.crypto import decrypt_value
from ekomek_common.outbox import enqueue_event

from .adapters import get_ecp_adapter
from .exceptions import EcpVerificationError
from ..models import EcpVerification


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return parse_datetime(value)


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    parsed = parse_date(str(value)[:10])
    return parsed


def store_verification(fields):
    record = EcpVerification(
        full_name=fields.get("full_name") or "",
        birth_date=_parse_date(fields.get("birth_date")),
        certificate_type=fields.get("certificate_type") or "",
        serial_number=fields.get("serial_number") or "",
        issuer=fields.get("issuer") or "",
        valid_from=_parse_datetime(fields.get("valid_from")),
        valid_to=_parse_datetime(fields.get("valid_to")),
        fingerprint=fields.get("fingerprint") or "",
        cms_hash=fields.get("cms_hash") or "",
        adapter=fields.get("adapter") or "",
        revocation_checked=bool(fields.get("revocation_checked")),
    )
    record.assign_iin(fields["iin"])
    record.save()
    enqueue_event(
        "ecp.verified",
        "ecp_verification",
        record.id,
        {
            "verification_id": record.id,
            "iin_hash": record.iin_hash,
            "iin_masked": record.iin_masked,
            "adapter": record.adapter,
            "certificate_type": record.certificate_type,
            "serial_number": record.serial_number,
            "issuer": record.issuer,
        },
    )
    return record


def verify_cms(challenge, cms):
    if not challenge or not cms:
        raise EcpVerificationError("Не переданы challenge или CMS-подпись.")
    if isinstance(challenge, str):
        challenge_bytes = challenge.encode("utf-8")
    else:
        challenge_bytes = challenge
    fields = get_ecp_adapter().verify(challenge_bytes, cms)
    record = store_verification(fields)
    return record, fields["iin"]


def serialize_verification(record, include_iin=False, request=None):
    payload = {
        "verification_id": record.id,
        "full_name": record.full_name,
        "iin_masked": record.iin_masked,
        "iin_hash": record.iin_hash,
        "birth_date": record.birth_date.isoformat() if record.birth_date else None,
        "certificate_type": record.certificate_type,
        "serial_number": record.serial_number,
        "issuer": record.issuer,
        "valid_from": record.valid_from.isoformat() if record.valid_from else None,
        "valid_to": record.valid_to.isoformat() if record.valid_to else None,
        "adapter": record.adapter,
        "revocation_checked": record.revocation_checked,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
    if include_iin:
        payload["iin"] = reveal_encrypted(
            record.iin_encrypted,
            resource_type="ecp_verification",
            resource_id=record.id,
            field_name="iin",
            purpose="identity_registration",
            request=request,
            actor_role="internal",
        ) or decrypt_value(record.iin_encrypted)
    return payload

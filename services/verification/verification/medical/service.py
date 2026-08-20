from ..services import FraudProfileRepository, serialize_fraud_profile
from .adapters import get_medical_adapter
from .exceptions import MedicalSourceConfigError, MedicalSourceUnavailable
from .normalize import (
    age_from_birth_date,
    gender_from_iin,
    gender_from_value,
    identity_fields,
    names_conflict,
    parse_birth_date,
)

REQUIRED_FIELDS = ("full_name", "birth_date", "city", "diagnosis")


def _fraud_payload(iin):
    profile = FraudProfileRepository().get_by_iin(iin)
    if profile is None:
        return None
    return serialize_fraud_profile(profile)


def _empty_medical():
    return {
        "found": False,
        "unavailable": False,
        "source": "",
        "full_name": "",
        "birth_date": None,
        "gender": "",
        "city": "",
        "clinic": "",
        "diagnosis": "",
    }


def lookup_medical(iin):
    try:
        return get_medical_adapter().lookup(iin)
    except MedicalSourceConfigError:
        result = _empty_medical()
        result["unavailable"] = True
        result["source"] = "unconfigured"
        return result
    except MedicalSourceUnavailable:
        result = _empty_medical()
        result["unavailable"] = True
        result["source"] = "official"
        return result


def merge_recipient_snapshot(iin, identity=None, medical=None):
    identity = identity or {}
    medical = medical or _empty_medical()
    birth_date = parse_birth_date(medical.get("birth_date") or identity.get("birth_date"))
    full_name = medical.get("full_name") or identity.get("full_name") or ""
    gender = gender_from_value(medical.get("gender")) or gender_from_iin(iin)
    snapshot = {
        **identity_fields(iin),
        "full_name": full_name,
        "birth_date": birth_date.isoformat() if birth_date else None,
        "age": age_from_birth_date(birth_date),
        "gender": gender,
        "city": medical.get("city") or "",
        "clinic": medical.get("clinic") or "",
        "diagnosis": medical.get("diagnosis") or "",
        "source": medical.get("source") or "",
        "found": bool(medical.get("found")),
        "unavailable": bool(medical.get("unavailable")),
        "is_self": False,
    }
    reasons = []
    if medical.get("unavailable"):
        reasons.append("medical_source_unavailable")
    elif not medical.get("found"):
        reasons.append("medical_record_not_found")
    if names_conflict(identity.get("full_name"), medical.get("full_name")):
        reasons.append("name_mismatch")
        snapshot["inconsistent"] = True
    else:
        snapshot["inconsistent"] = False
    missing = [field for field in REQUIRED_FIELDS if not snapshot.get(field)]
    snapshot["incomplete"] = bool(missing or medical.get("unavailable") or not medical.get("found"))
    if missing:
        reasons.append("incomplete_medical_data")
    snapshot["review_reasons"] = reasons
    return snapshot


def verify_recipient(iin, *, author_iin_hash="", identity=None):
    medical = lookup_medical(iin)
    snapshot = merge_recipient_snapshot(iin, identity=identity, medical=medical)
    author_hash = author_iin_hash or ""
    snapshot["is_self"] = bool(author_hash and snapshot["iin_hash"] == author_hash)
    fraud = _fraud_payload(iin)
    snapshot["blocked"] = bool(fraud and fraud.get("blocked"))
    snapshot["high_risk"] = bool(fraud and (fraud.get("blocked") or fraud.get("needs_review")))
    snapshot["risk_score"] = (fraud or {}).get("risk_score") or 0
    snapshot["fraud_reasons"] = (fraud or {}).get("reasons") or []
    if snapshot["high_risk"]:
        snapshot["review_reasons"] = list(snapshot["review_reasons"]) + ["high_risk"]
    if snapshot["incomplete"] or snapshot["inconsistent"] or snapshot["high_risk"] or snapshot["unavailable"]:
        snapshot["requires_manual_review"] = True
    else:
        snapshot["requires_manual_review"] = False
    return snapshot

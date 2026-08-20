from ekomek_common.constants import (
    BeneficiaryStatus,
    CardStatus,
    PUBLIC_CARD_STATUSES,
    RepresentationStatus,
)
from ekomek_common.http import ServiceClientError, documents_client, expenses_client, identity_client, profile_client

BADGE_LABELS = {
    "author_eds_verified": "ЭЦП автора подтверждена",
    "beneficiary_verified": "Получатель подтверждён",
    "representation_verified": "Представительство подтверждено",
    "documents_verified": "Документы проверены",
    "diagnosis_verified": "Диагноз подтверждён",
    "clinic_verified": "Медицинская организация подтверждена",
    "moderator_approved": "Сбор проверен модератором",
    "expenses_verified": "Расходы подтверждены документами",
}


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _safe_get(client_factory, path):
    try:
        return client_factory().get(path)
    except ServiceClientError:
        return None


def _badge(code, verified, verified_at=None):
    return {
        "code": code,
        "label": BADGE_LABELS[code],
        "verified": bool(verified),
        "verified_at": _iso(verified_at) if verified else None,
    }


def _author_eds_badge(card):
    user = _safe_get(identity_client, f"/internal/users/{card.author_id}/") or {}
    verified = bool(user.get("ecp_verification_id"))
    if not verified:
        return _badge("author_eds_verified", False)
    return _badge("author_eds_verified", True, user.get("updated_at") or user.get("created_at"))


def _beneficiary_badge(card):
    if not card.beneficiary_id:
        return _badge("beneficiary_verified", False)
    payload = _safe_get(profile_client, f"/internal/beneficiaries/{card.beneficiary_id}/") or {}
    verified = payload.get("verification_status") == BeneficiaryStatus.VERIFIED
    return _badge("beneficiary_verified", verified, payload.get("verified_at") if verified else None)


def _representation_badge(card):
    if card.is_self or card.relationship_type == "self":
        return _badge("representation_verified", False)
    if not card.representation_id:
        return _badge("representation_verified", False)
    payload = _safe_get(profile_client, f"/internal/representations/{card.representation_id}/") or {}
    verified = payload.get("verification_status") == RepresentationStatus.VERIFIED
    return _badge("representation_verified", verified, payload.get("verified_at") if verified else None)


def _documents_badge(card):
    documents = _safe_get(documents_client, f"/internal/cards/{card.id}/documents/") or []
    if not isinstance(documents, list) or not documents:
        return _badge("documents_verified", False)
    pending = {"uploaded", "under_review"}
    verified_docs = [item for item in documents if item.get("status") == "verified"]
    has_pending = any(item.get("status") in pending for item in documents)
    verified = bool(verified_docs) and not has_pending
    latest = max((item.get("updated_at") or item.get("created_at") for item in verified_docs), default=None)
    return _badge("documents_verified", verified, latest if verified else None)


def _expenses_badge(card):
    totals = _safe_get(expenses_client, f"/internal/cards/{card.id}/totals/") or {}
    count = int(totals.get("approved_count") or 0)
    verified = count > 0
    return _badge("expenses_verified", verified, totals.get("last_approved_at") if verified else None)


def _moderator_badge(card):
    verified = bool(card.moderation_verified_at) and card.status in PUBLIC_CARD_STATUSES | {CardStatus.SUSPENDED}
    return _badge("moderator_approved", verified, card.moderation_verified_at if verified else None)


def build_trust_status(card):
    badges = [
        _author_eds_badge(card),
        _beneficiary_badge(card),
        _representation_badge(card),
        _documents_badge(card),
        _badge("diagnosis_verified", bool(card.diagnosis_verified_at), card.diagnosis_verified_at),
        _badge("clinic_verified", bool(card.clinic_verified_at), card.clinic_verified_at),
        _moderator_badge(card),
        _expenses_badge(card),
    ]
    verified_dates = [item["verified_at"] for item in badges if item["verified"] and item["verified_at"]]
    return {
        "card_id": card.id,
        "badges": badges,
        "last_verified_at": max(verified_dates) if verified_dates else None,
    }

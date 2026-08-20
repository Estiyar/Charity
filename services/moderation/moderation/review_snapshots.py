from ekomek_common.http import ServiceClientError, cards_client, documents_client, identity_client, verification_client

DOCUMENT_META_FIELDS = (
    "id",
    "card_id",
    "file_name",
    "file_type",
    "status",
    "has_confidential",
    "created_at",
)
HIDDEN_KEYS = {"iin", "cms", "phone", "iin_encrypted"}


def strip_sensitive(value):
    if isinstance(value, dict):
        return {
            key: strip_sensitive(item)
            for key, item in value.items()
            if key.lower() not in HIDDEN_KEYS
        }
    if isinstance(value, list):
        return [strip_sensitive(item) for item in value]
    return value


def _safe_get(client_factory, path):
    try:
        return client_factory().get(path)
    except ServiceClientError:
        return None


def fetch_fraud(iin_hash):
    if not iin_hash:
        return None
    return _safe_get(verification_client, f"/internal/antifraud/hash/{iin_hash}/")


def fetch_medical(iin_hash):
    if not iin_hash:
        return None
    return _safe_get(verification_client, f"/internal/medregistry/hash/{iin_hash}/")


def fetch_ecp(verification_id):
    if not verification_id:
        return None
    return _safe_get(verification_client, f"/internal/ecp/verifications/{verification_id}/")


def document_metadata(card_id):
    documents = _safe_get(documents_client, f"/internal/cards/{card_id}/documents/") or []
    metadata = []
    for document in documents:
        metadata.append({field: document.get(field) for field in DOCUMENT_META_FIELDS})
    return metadata


def duplicate_signals_from(reasons):
    signals = []
    for reason in reasons or []:
        text = str(reason)
        if "duplicate" in text.lower():
            signals.append(text)
    return signals


def card_duplicate_signals(card, reasons):
    structured = []
    for item in card.get("duplicate_signals") or []:
        if isinstance(item, dict):
            structured.append(
                {
                    "code": item.get("code") or "",
                    "message": item.get("message") or "",
                    "matched_card_ids": item.get("matched_card_ids") or [],
                }
            )
        elif item:
            structured.append(item)
    for extra in duplicate_signals_from(reasons):
        codes = {item.get("code") for item in structured if isinstance(item, dict)}
        if extra not in structured and extra not in codes:
            structured.append(extra)
    return structured


def risk_level_from_score(score):
    if score > 80:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _risk_fields(fraud, extra_reasons=None, duplicate_risk_delta=0):
    score = int((fraud or {}).get("risk_score") or 0) + int(duplicate_risk_delta or 0)
    score = min(score, 100)
    reasons = list((fraud or {}).get("reasons") or [])
    for reason in extra_reasons or []:
        if reason not in reasons:
            reasons.append(reason)
    level = (fraud or {}).get("risk_level") or risk_level_from_score(score)
    return score, level, reasons


def assemble_user_snapshot(user_id, payload=None):
    payload = payload or {}
    user = _safe_get(identity_client, f"/internal/users/{user_id}/") or payload
    iin_hash = user.get("iin_hash") or payload.get("iin_hash")
    fraud = fetch_fraud(iin_hash)
    score, level, reasons = _risk_fields(fraud)
    verification = strip_sensitive(
        {
            "fraud": fraud,
            "medical": fetch_medical(iin_hash),
            "ecp": fetch_ecp(user.get("ecp_verification_id")),
            "user_status": user.get("status"),
            "role": user.get("role"),
            "iin_masked": user.get("iin_masked"),
            "iin_hash": iin_hash,
        }
    )
    return {
        "subject_label": user.get("full_name") or user.get("email") or f"user:{user_id}",
        "risk_score": score,
        "risk_level": level,
        "risk_reasons": reasons,
        "verification_snapshot": verification,
        "duplicate_signals": duplicate_signals_from(reasons),
        "document_metadata": [],
        "previous_subject_status": user.get("status") or payload.get("status") or "",
        "evidence_snapshot": {
            "user_id": user_id,
            "status": user.get("status"),
            "role": user.get("role"),
            "iin_masked": user.get("iin_masked"),
        },
    }


def assemble_card_snapshot(card_id, payload=None):
    payload = payload or {}
    card = _safe_get(cards_client, f"/internal/cards/{card_id}/") or payload
    iin_hash = card.get("iin_hash") or payload.get("iin_hash")
    extra_reasons = card.get("review_reasons") or payload.get("reasons") or []
    fraud = fetch_fraud(iin_hash)
    score, level, reasons = _risk_fields(fraud, extra_reasons, card.get("duplicate_risk_delta") or 0)
    verification = strip_sensitive(
        {
            "fraud": fraud,
            "medical": fetch_medical(iin_hash),
            "card_status": card.get("status"),
            "high_risk": card.get("high_risk"),
            "needs_extra_review": card.get("needs_extra_review"),
            "duplicate_suspected": card.get("duplicate_suspected"),
            "iin_masked": card.get("iin_masked"),
            "iin_hash": iin_hash,
        }
    )
    metadata = document_metadata(card_id)
    return {
        "subject_label": card.get("full_name") or f"card:{card_id}",
        "risk_score": score,
        "risk_level": level,
        "risk_reasons": reasons,
        "verification_snapshot": verification,
        "duplicate_signals": card_duplicate_signals(card, reasons),
        "document_metadata": metadata,
        "previous_subject_status": card.get("status") or "",
        "evidence_snapshot": {
            "card_id": card_id,
            "status": card.get("status"),
            "high_risk": card.get("high_risk"),
            "review_reasons": extra_reasons,
            "iin_masked": card.get("iin_masked"),
            "duplicate_matches": card.get("duplicate_matches") or [],
            "document_ids": [item.get("id") for item in metadata],
        },
    }

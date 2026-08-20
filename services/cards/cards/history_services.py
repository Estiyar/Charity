from ekomek_common.constants import POST_ACTIVATION_STATUSES, CardStatus, InvalidStatusTransition
from ekomek_common.outbox import enqueue_event

from .history_constants import (
    CRITICAL_FIELDS,
    EVENT_SUMMARIES,
    FIELD_EVENT_TYPES,
    HIDDEN_PAYLOAD_KEYS,
    PUBLIC_HISTORY_TYPES,
)
from .models import CardHistoryEvent


def _actor_fields(actor):
    return {
        "actor_id": getattr(actor, "id", None),
        "actor_role": getattr(actor, "role", "") or "",
    }


def sanitize_payload(payload):
    if not isinstance(payload, dict):
        return {}
    return {key: value for key, value in payload.items() if key.lower() not in HIDDEN_PAYLOAD_KEYS}


def record_card_event(card, event_type, *, payload=None, actor=None, public=None, summary=None):
    is_public = PUBLIC_HISTORY_TYPES.__contains__(event_type) if public is None else public
    if event_type == "payout_details_changed":
        is_public = False
    if event_type == "beneficiary_changed":
        is_public = False
    return CardHistoryEvent.objects.create(
        card=card,
        event_type=event_type,
        summary=summary or EVENT_SUMMARIES.get(event_type) or event_type,
        public=is_public,
        payload=sanitize_payload(payload or {}),
        **_actor_fields(actor),
    )


def _stringify(value):
    if value is None:
        return ""
    return str(value)


SAFE_VALUE_FIELDS = frozenset({"target_amount", "diagnosis", "description", "end_date", "clinic"})


def record_field_changes(card, changes, actor=None):
    events = []
    beneficiary_touched = "beneficiary_id" in changes or "iin_hash" in changes
    for field, (old, new) in changes.items():
        if field in ("beneficiary_id", "iin_hash") and beneficiary_touched:
            continue
        event_type = FIELD_EVENT_TYPES.get(field)
        if not event_type:
            continue
        payload = {"field": field}
        if field in SAFE_VALUE_FIELDS:
            payload["old"] = _stringify(old)
            payload["new"] = _stringify(new)
        events.append(record_card_event(card, event_type, actor=actor, payload=payload))
    if beneficiary_touched:
        events.append(
            record_card_event(
                card,
                "beneficiary_changed",
                actor=actor,
                payload={"changed": True},
            )
        )
    return events


def record_status_change(card, previous, target, actor=None, comment=""):
    payload = {"previous_status": previous, "status": target}
    if comment:
        payload["comment"] = comment
    if previous != CardStatus.SUSPENDED and target == CardStatus.SUSPENDED:
        record_card_event(card, "suspended", actor=actor, payload=payload)
    elif previous == CardStatus.SUSPENDED and target != CardStatus.SUSPENDED:
        record_card_event(card, "unsuspended", actor=actor, payload=payload)
    if target in (CardStatus.ACTIVE, CardStatus.REJECTED, CardStatus.REVISION_REQUIRED):
        record_card_event(card, "moderation_decision", actor=actor, payload=payload)
    record_card_event(card, "status_changed", actor=actor, payload=payload)
    return card


def request_remoderation(card, reasons, actor=None):
    from .services import transition_card

    if card.status not in POST_ACTIVATION_STATUSES:
        return card
    card.moderation_verified_at = None
    card.needs_extra_review = True
    merged = list(card.review_reasons or [])
    for reason in reasons:
        if reason not in merged:
            merged.append(reason)
    card.review_reasons = merged
    card.save(update_fields=["moderation_verified_at", "needs_extra_review", "review_reasons", "updated_at"])
    if card.status != CardStatus.MANUAL_REVIEW:
        try:
            transition_card(card, CardStatus.MANUAL_REVIEW, actor=actor)
        except InvalidStatusTransition:
            card.status = CardStatus.MANUAL_REVIEW
            card.save(update_fields=["status", "updated_at"])
    enqueue_event(
        "card.manual_review_required",
        "card",
        card.id,
        {"card_id": card.id, "reasons": card.review_reasons},
    )
    return card


def apply_card_field_updates(card, validated_data, actor=None):
    tracked = set(FIELD_EVENT_TYPES) | {"beneficiary_id", "iin_hash"}
    changes = {}
    for field, value in validated_data.items():
        current = getattr(card, field, None)
        if current != value:
            if field in tracked:
                changes[field] = (current, value)
            setattr(card, field, value)
    if "diagnosis" in changes:
        card.diagnosis_verified_at = None
    if "clinic" in changes:
        card.clinic_verified_at = None
    card.save()
    record_field_changes(card, changes, actor=actor)
    critical = [field for field in changes if field in CRITICAL_FIELDS]
    if critical:
        request_remoderation(card, [f"critical_change:{field}" for field in critical], actor=actor)
    from .business_limits import (
        check_beneficiary_change_allowed,
        check_clinic_change,
        check_payout_change,
        check_target_amount_change,
    )

    if "beneficiary_id" in changes or "iin_hash" in changes:
        check_beneficiary_change_allowed(card)
    needs_reverification = False
    if "target_amount" in changes:
        if check_target_amount_change(card, validated_data.get("target_amount")):
            needs_reverification = True
    if "clinic" in changes:
        if check_clinic_change(card, validated_data.get("clinic")):
            needs_reverification = True
    if "payout_details_hash" in changes:
        new_hash = validated_data.get("payout_details_hash") or ""
        if check_payout_change(card, new_hash):
            needs_reverification = True
    if needs_reverification and not critical:
        request_remoderation(card, ["business_limit_reverification"], actor=actor)
    return card


def public_timeline(card):
    return card.history_events.filter(public=True)


def staff_history(card):
    return card.history_events.all()

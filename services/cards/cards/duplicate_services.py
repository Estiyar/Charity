import json

from django.db import IntegrityError
from django.utils import timezone

from ekomek_common.crypto import hmac_hash
from ekomek_common.http import ServiceClientError, documents_client
from ekomek_common.outbox import enqueue_event

from .duplicate_signals import (
    build_matches,
    collect_hard_signals,
    collect_soft_signals,
    has_hard_duplicate,
    risk_delta_for,
)
from .duplicate_text import normalize_text
from .models import DuplicateCheck, FundraisingCard
from .repositories import CardRepository


def client_fingerprint_hash(request):
    if request is None:
        return ""
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    ip_address = forwarded or request.META.get("REMOTE_ADDR") or ""
    user_agent = request.META.get("HTTP_USER_AGENT") or ""
    if not ip_address and not user_agent:
        return ""
    return hmac_hash(f"{ip_address}|{user_agent}")


def capture_request_fingerprint(card, request):
    fingerprint = client_fingerprint_hash(request)
    if not fingerprint or card.request_fingerprint_hash == fingerprint:
        return card
    card.request_fingerprint_hash = fingerprint
    card.save(update_fields=["request_fingerprint_hash", "updated_at"])
    return card


def _document_file_hashes(card):
    try:
        matches = documents_client().get("/internal/documents/duplicates/", params={"card_id": card.id})
    except ServiceClientError:
        return [], []
    hashes = sorted({item.get("file_hash") or "" for item in matches or [] if item.get("file_hash")})
    matched_ids = {item.get("card_id") for item in matches or [] if item.get("card_id")}
    document_cards = list(FundraisingCard.objects.filter(pk__in=matched_ids).exclude(pk=card.pk))
    return hashes, document_cards


def _check_fingerprint(card, document_hashes):
    payload = {
        "iin_hash": card.iin_hash or "",
        "document_number_hash": card.document_number_hash or "",
        "diagnosis": normalize_text(card.diagnosis),
        "description": normalize_text(card.description),
        "author_id": card.author_id,
        "payout_details_hash": card.payout_details_hash or "",
        "request_fingerprint_hash": card.request_fingerprint_hash or "",
        "document_file_hashes": document_hashes,
    }
    return hmac_hash(json.dumps(payload, sort_keys=True, ensure_ascii=True))


def _merge_review_reasons(existing, signals, suspected):
    reasons = list(existing or [])
    if suspected and "duplicate_suspected" not in reasons:
        reasons.append("duplicate_suspected")
    for signal in signals:
        marker = f"duplicate:{signal['code']}"
        if marker not in reasons:
            reasons.append(marker)
    return reasons


def _write_card_from_check(card, check):
    suspected = bool(check.suspected)
    card.duplicate_suspected = suspected
    card.duplicate_signals = check.signals
    card.duplicate_matches = check.matches
    card.duplicate_fingerprint = check.fingerprint
    card.duplicate_risk_delta = check.risk_delta
    card.duplicate_checked_at = timezone.now()
    card.review_reasons = _merge_review_reasons(card.review_reasons, check.signals, suspected)
    if suspected or any(signal["code"].startswith("high_volume") for signal in check.signals):
        card.needs_extra_review = True
    if check.risk_delta >= 20:
        card.high_risk = True
    card.save(
        update_fields=[
            "duplicate_suspected",
            "duplicate_signals",
            "duplicate_matches",
            "duplicate_fingerprint",
            "duplicate_risk_delta",
            "duplicate_checked_at",
            "review_reasons",
            "needs_extra_review",
            "high_risk",
            "updated_at",
        ]
    )
    return card


def _store_check(card, fingerprint, signals, matches, risk_delta, suspected):
    try:
        check = DuplicateCheck.objects.create(
            card=card,
            fingerprint=fingerprint,
            suspected=suspected,
            signals=signals,
            matches=matches,
            risk_delta=risk_delta,
        )
        created = True
    except IntegrityError:
        check = DuplicateCheck.objects.get(card=card, fingerprint=fingerprint)
        created = False
    _write_card_from_check(card, check)
    if created and suspected:
        enqueue_event(
            "card.duplicate_detected",
            "card",
            card.id,
            {
                "card_id": card.id,
                "duplicate_suspected": True,
                "signals": [signal["code"] for signal in signals],
                "matched_card_ids": [item["card_id"] for item in matches],
            },
        )
    return check


def apply_duplicate_check(card, request=None):
    if request is not None:
        capture_request_fingerprint(card, request)
    repository = CardRepository()
    document_hashes, document_cards = _document_file_hashes(card)
    fingerprint = _check_fingerprint(card, document_hashes)
    existing = DuplicateCheck.objects.filter(card=card, fingerprint=fingerprint).first()
    if existing:
        if card.duplicate_fingerprint != fingerprint:
            _write_card_from_check(card, existing)
        return existing
    candidates = list(repository.duplicate_candidates(card))
    for item in document_cards:
        if item.id != card.id and item not in candidates:
            candidates.append(item)
    signals = collect_hard_signals(card, candidates, document_cards)
    signals.extend(
        collect_soft_signals(
            list(repository.other_author_cards(card)),
            list(repository.other_fingerprint_cards(card)),
        )
    )
    matches = build_matches(candidates + document_cards, signals)
    suspected = has_hard_duplicate(signals)
    return _store_check(card, fingerprint, signals, matches, risk_delta_for(signals), suspected)


def mark_duplicate_override(card):
    if card.duplicate_override:
        return card
    card.duplicate_override = True
    card.save(update_fields=["duplicate_override", "updated_at"])
    return card

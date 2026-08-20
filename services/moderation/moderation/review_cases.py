from django.db import IntegrityError

from ekomek_common.constants import CardStatus, UserStatus
from ekomek_common.outbox import enqueue_event

from .models import ManualReviewCase
from .review_snapshots import assemble_card_snapshot, assemble_user_snapshot

QUEUEABLE_CARD_STATUSES = {
    CardStatus.MANUAL_REVIEW,
    CardStatus.PENDING_MODERATION,
    CardStatus.REVISION_REQUIRED,
    CardStatus.SUSPENDED,
}


def apply_snapshot(case, snapshot):
    case.subject_label = snapshot.get("subject_label") or case.subject_label
    case.risk_score = snapshot.get("risk_score") or 0
    case.risk_level = snapshot.get("risk_level") or ""
    case.risk_reasons = snapshot.get("risk_reasons") or []
    case.verification_snapshot = snapshot.get("verification_snapshot") or {}
    case.duplicate_signals = snapshot.get("duplicate_signals") or []
    case.document_metadata = snapshot.get("document_metadata") or []
    case.evidence_snapshot = snapshot.get("evidence_snapshot") or {}
    if snapshot.get("previous_subject_status"):
        case.previous_subject_status = snapshot["previous_subject_status"]


def _emit_opened(case):
    enqueue_event(
        "review.opened",
        "review",
        case.id,
        {
            "case_id": case.id,
            "subject_type": case.subject_type,
            "subject_id": case.subject_id,
            "risk_score": case.risk_score,
            "risk_level": case.risk_level,
        },
    )


def upsert_case(subject_type, subject_id, snapshot):
    open_case = ManualReviewCase.objects.filter(
        subject_type=subject_type,
        subject_id=subject_id,
        status=ManualReviewCase.Status.OPEN,
    ).first()
    if open_case:
        return open_case, False
    reopen = (
        ManualReviewCase.objects.filter(subject_type=subject_type, subject_id=subject_id)
        .filter(status=ManualReviewCase.Status.REVISION_REQUIRED)
        .order_by("-opened_at")
        .first()
    )
    if reopen:
        apply_snapshot(reopen, snapshot)
        reopen.status = ManualReviewCase.Status.OPEN
        reopen.save()
        _emit_opened(reopen)
        return reopen, True
    case = ManualReviewCase(subject_type=subject_type, subject_id=subject_id)
    apply_snapshot(case, snapshot)
    case.status = ManualReviewCase.Status.OPEN
    try:
        case.save()
    except IntegrityError:
        existing = ManualReviewCase.objects.filter(
            subject_type=subject_type,
            subject_id=subject_id,
            status=ManualReviewCase.Status.OPEN,
        ).first()
        if existing:
            return existing, False
        raise
    _emit_opened(case)
    return case, True


def should_open_user_review(payload):
    return payload.get("status") == UserStatus.MANUAL_REVIEW


def should_open_card_review(card):
    if not card:
        return False
    if card.get("status") == CardStatus.MANUAL_REVIEW:
        return True
    if card.get("status") not in QUEUEABLE_CARD_STATUSES:
        return False
    return bool(card.get("high_risk") or card.get("needs_extra_review"))


def open_user_review(payload):
    if not should_open_user_review(payload):
        return None
    user_id = int(payload["user_id"])
    snapshot = assemble_user_snapshot(user_id, payload)
    case, _created = upsert_case(ManualReviewCase.SubjectType.USER, user_id, snapshot)
    return case


def open_card_review(payload):
    card_id = int(payload.get("card_id") or payload.get("subject_id") or 0)
    if not card_id:
        return None
    snapshot = assemble_card_snapshot(card_id, payload)
    card = snapshot.get("evidence_snapshot") or payload
    merged = {
        "status": snapshot["previous_subject_status"] or payload.get("status"),
        "high_risk": card.get("high_risk") or payload.get("high_risk"),
        "needs_extra_review": payload.get("needs_extra_review"),
    }
    if not should_open_card_review({**payload, **merged}):
        return None
    case, _created = upsert_case(ManualReviewCase.SubjectType.CARD, card_id, snapshot)
    return case

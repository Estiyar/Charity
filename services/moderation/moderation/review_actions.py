from django.db import IntegrityError, transaction

from ekomek_common.constants import CardStatus, UserStatus
from ekomek_common.http import ServiceClientError, identity_client
from ekomek_common.outbox import enqueue_event

from .models import ManualReviewCase, ReviewDecision
from .review_policy import (
    ACTION_CASE_STATUS,
    COMMENT_REQUIRED_ACTIONS,
    DEFAULT_EVIDENCE,
    allowed_actions,
    approved_user_status,
    case_status_after_unsuspend,
)
from .services import ModerationActionError, fetch_card, log_moderation_action, transition


def _identity_set_status(user_id, status, reason):
    try:
        return identity_client().post(
            f"/internal/users/{user_id}/set-status/",
            json={"status": status, "reason": reason},
        )
    except ServiceClientError as exc:
        detail = (exc.payload or {}).get("detail") or str(exc)
        raise ModerationActionError(detail) from exc


def _identity_user(user_id):
    try:
        return identity_client().get(f"/internal/users/{user_id}/")
    except ServiceClientError as exc:
        detail = (exc.payload or {}).get("detail") or str(exc)
        raise ModerationActionError(detail) from exc


def _transition_card(card_id, target, comment, duplicate_override=False, *, moderator=None, internal_comment=""):
    try:
        return transition(
            card_id,
            target,
            comment,
            duplicate_override=duplicate_override,
            moderator=moderator,
            internal_comment=internal_comment,
        )
    except ModerationActionError:
        card = fetch_card(card_id)
        if card and card.get("status") == target:
            return card
        raise


def apply_user_action(case, action, comment):
    if action == "request_revision":
        return None
    if action == "approve":
        user = _identity_user(case.subject_id)
        return _identity_set_status(case.subject_id, approved_user_status(user), comment)
    if action == "reject":
        return _identity_set_status(case.subject_id, UserStatus.REJECTED, comment)
    if action == "suspend":
        user = _identity_user(case.subject_id)
        case.previous_subject_status = user.get("status") or case.previous_subject_status
        return _identity_set_status(case.subject_id, UserStatus.BLOCKED, comment)
    restored = case.previous_subject_status or UserStatus.MANUAL_REVIEW
    return _identity_set_status(case.subject_id, restored, comment)


def apply_card_action(case, action, comment, moderator, internal_comment=""):
    targets = {
        "approve": CardStatus.ACTIVE,
        "reject": CardStatus.REJECTED,
        "request_revision": CardStatus.REVISION_REQUIRED,
        "suspend": CardStatus.SUSPENDED,
        "unsuspend": case.previous_subject_status or CardStatus.MANUAL_REVIEW,
    }
    if action == "suspend":
        card = fetch_card(case.subject_id)
        if card:
            case.previous_subject_status = card.get("status") or case.previous_subject_status
    updated = _transition_card(
        case.subject_id,
        targets[action],
        comment,
        duplicate_override=action == "approve",
        moderator=moderator,
        internal_comment=internal_comment,
    )
    log_moderation_action(updated, moderator, action, comment)
    return updated


def _decision_key(case, action, idempotency_key):
    if idempotency_key:
        return idempotency_key
    return f"{case.id}:{action}:{case.status}"


def _target_case_status(case, action):
    if action == "unsuspend":
        return case_status_after_unsuspend(case.previous_subject_status)
    return ACTION_CASE_STATUS[action]


def apply_review_decision(
    case_id,
    action,
    moderator,
    comment="",
    evidence_reviewed=None,
    idempotency_key="",
    internal_comment="",
):
    if action in COMMENT_REQUIRED_ACTIONS and not comment:
        raise ModerationActionError("Комментарий обязателен.")
    with transaction.atomic():
        case = ManualReviewCase.objects.select_for_update().get(pk=case_id)
        key = _decision_key(case, action, idempotency_key)
        existing = ReviewDecision.objects.filter(case=case, idempotency_key=key).first()
        if existing:
            latest = case.decisions.order_by("-created_at", "-id").first()
            if latest is not None and latest.pk != existing.pk:
                return case
            synced = _target_case_status(case, existing.action)
            if case.status != synced:
                case.status = synced
                case.save(update_fields=["status", "updated_at"])
            return case
        if action not in allowed_actions(case):
            raise ModerationActionError("Это действие недоступно для текущей проверки.")
        target_status = _target_case_status(case, action)
        if case.status == target_status:
            return case
        if case.subject_type == ManualReviewCase.SubjectType.USER:
            apply_user_action(case, action, comment)
        else:
            apply_card_action(case, action, comment, moderator, internal_comment=internal_comment)
        from .comment_services import record_moderation_comments

        record_moderation_comments(
            target_type="review",
            target_id=case.id,
            revision_body=comment,
            internal_body=internal_comment,
            actor=moderator,
            review_id=case.id,
        )
        try:
            ReviewDecision.objects.create(
                case=case,
                action=action,
                moderator_id=getattr(moderator, "id", 0) or 0,
                moderator_name=getattr(moderator, "full_name", "") or "",
                comment=comment,
                evidence_reviewed=evidence_reviewed or DEFAULT_EVIDENCE,
                idempotency_key=key,
            )
        except IntegrityError:
            return ManualReviewCase.objects.get(pk=case.id)
        case.status = target_status
        case.save()
        enqueue_event(
            "review.decision_applied",
            "review",
            case.id,
            {
                "case_id": case.id,
                "subject_type": case.subject_type,
                "subject_id": case.subject_id,
                "action": action,
                "moderator_id": getattr(moderator, "id", None),
            },
        )
        enqueue_event(
            "moderation.decision_created",
            "moderation",
            case.subject_id,
            {"action": action, "subject_type": case.subject_type, "subject_id": case.subject_id},
        )
        return case

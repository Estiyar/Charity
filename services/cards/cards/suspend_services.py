from ekomek_common.audit import log_sensitive_access
from ekomek_common.constants import CardStatus, InvalidStatusTransition

from .services import transition_card


class SuspendActionError(Exception):
    pass


SUSPENDABLE_STATUSES = {
    CardStatus.ACTIVE,
    CardStatus.MANUAL_REVIEW,
    CardStatus.PENDING_MODERATION,
    CardStatus.APPROVED,
    CardStatus.COMPLETED,
    CardStatus.REDISTRIBUTION,
}


def suspend_card(card, reason, actor=None, *, source="moderation"):
    reason = (reason or "").strip()
    if not reason:
        raise SuspendActionError("Причина приостановки обязательна.")
    if card.status == CardStatus.SUSPENDED:
        return card
    if card.status not in SUSPENDABLE_STATUSES:
        raise SuspendActionError("Этот сбор нельзя приостановить в текущем статусе.")
    card.status_before_suspend = card.status
    card.suspend_reason = reason
    card.save(update_fields=["status_before_suspend", "suspend_reason", "updated_at"])
    try:
        transition_card(card, CardStatus.SUSPENDED, actor=actor, comment=reason)
    except InvalidStatusTransition as exc:
        raise SuspendActionError(str(exc)) from exc
    if actor is not None:
        log_sensitive_access(
            resource_type="card",
            resource_id=card.id,
            field_name="status",
            purpose=f"suspend:{source}",
            actor_id=getattr(actor, "id", None),
            actor_role=getattr(actor, "role", "") or "",
        )
    return card


def unsuspend_card(card, reason, actor=None):
    reason = (reason or "").strip()
    if not reason:
        raise SuspendActionError("Причина снятия приостановки обязательна.")
    if card.status != CardStatus.SUSPENDED:
        raise SuspendActionError("Сбор не приостановлен.")
    target = card.status_before_suspend or CardStatus.MANUAL_REVIEW
    previous_reason = card.suspend_reason
    previous_status = card.status_before_suspend
    card.suspend_reason = ""
    card.status_before_suspend = ""
    card.save(update_fields=["suspend_reason", "status_before_suspend", "updated_at"])
    try:
        transition_card(card, target, actor=actor, comment=reason)
    except InvalidStatusTransition as exc:
        card.suspend_reason = previous_reason
        card.status_before_suspend = previous_status
        card.save(update_fields=["suspend_reason", "status_before_suspend", "updated_at"])
        raise SuspendActionError(str(exc)) from exc
    if actor is not None:
        log_sensitive_access(
            resource_type="card",
            resource_id=card.id,
            field_name="status",
            purpose="unsuspend",
            actor_id=getattr(actor, "id", None),
            actor_role=getattr(actor, "role", "") or "",
        )
    return card


def update_report_risk(card, report_risk_score, unique_report_count):
    card.report_risk_score = report_risk_score
    card.unique_report_count = unique_report_count
    card.save(update_fields=["report_risk_score", "unique_report_count", "updated_at"])
    return card

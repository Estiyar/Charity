from apps.common.card_status import CardStatus, InvalidStatusTransition, transition
from apps.moderation.models import ModerationLog


class ModerationActionError(Exception):
    pass


def log_moderation_action(card, moderator, action, comment=""):
    return ModerationLog.objects.create(
        card=card,
        moderator=moderator,
        action=action,
        comment=comment,
    )


def approve_card(card, moderator, comment=""):
    if card.status != CardStatus.PENDING_MODERATION:
        raise ModerationActionError("Одобрить можно только заявку на модерации.")
    try:
        transition(card, CardStatus.APPROVED)
        transition(card, CardStatus.ACTIVE)
    except InvalidStatusTransition as exc:
        raise ModerationActionError(str(exc)) from exc
    if comment:
        card.moderator_comment = comment
        card.save(update_fields=["moderator_comment", "updated_at"])
    log_moderation_action(card, moderator, "approve", comment)
    return card


def reject_card(card, moderator, comment):
    if not comment:
        raise ModerationActionError("Комментарий обязателен при отклонении.")
    if card.status != CardStatus.PENDING_MODERATION:
        raise ModerationActionError("Отклонить можно только заявку на модерации.")
    try:
        transition(card, CardStatus.REJECTED)
    except InvalidStatusTransition as exc:
        raise ModerationActionError(str(exc)) from exc
    card.moderator_comment = comment
    card.save(update_fields=["moderator_comment", "status", "updated_at"])
    log_moderation_action(card, moderator, "reject", comment)
    return card


def request_card_revision(card, moderator, comment):
    if not comment:
        raise ModerationActionError("Комментарий обязателен при отправке на доработку.")
    if card.status != CardStatus.PENDING_MODERATION:
        raise ModerationActionError("На доработку можно отправить только заявку на модерации.")
    try:
        transition(card, CardStatus.REVISION_REQUIRED)
    except InvalidStatusTransition as exc:
        raise ModerationActionError(str(exc)) from exc
    card.moderator_comment = comment
    card.save(update_fields=["moderator_comment", "status", "updated_at"])
    log_moderation_action(card, moderator, "request_revision", comment)
    return card

from ekomek_common.constants import CardStatus
from ekomek_common.http import ServiceClientError, cards_client, documents_client
from ekomek_common.outbox import enqueue_event

from .models import ModerationLog


class ModerationActionError(Exception):
    pass


CARD_REVIEW_STATUSES = {CardStatus.PENDING_MODERATION, CardStatus.MANUAL_REVIEW}


def fetch_card(card_id, actor=None):
    params = {}
    headers = {}
    if actor is not None:
        params["reveal"] = "1"
        actor_id = getattr(actor, "id", None)
        if actor_id is not None:
            headers["X-Actor-Id"] = str(actor_id)
        headers["X-Actor-Role"] = getattr(actor, "role", "") or ""
    try:
        return cards_client().get(f"/internal/cards/{card_id}/", params=params, headers=headers)
    except ServiceClientError:
        return None


def list_cards(status_filter=None):
    params = {}
    if status_filter:
        params["status"] = status_filter
    try:
        return cards_client().get("/internal/cards/", params=params)
    except ServiceClientError:
        return []


def fetch_documents(card_id):
    try:
        return documents_client().get(f"/internal/cards/{card_id}/documents/")
    except ServiceClientError:
        return []


def log_moderation_action(card, moderator, action, comment=""):
    return ModerationLog.objects.create(
        card_id=card["id"],
        card_name=card.get("full_name", ""),
        moderator_id=getattr(moderator, "id", None),
        moderator_name=getattr(moderator, "full_name", ""),
        action=action,
        comment=comment,
    )


def _comment_author_payload(moderator):
    return {
        "comment_author_id": getattr(moderator, "id", None),
        "comment_author_role": getattr(moderator, "role", "") or "",
        "comment_author_name": getattr(moderator, "full_name", "") or "",
    }


def transition(card_id, target, comment="", duplicate_override=False, *, moderator=None, internal_comment=""):
    payload = {"status": target, "comment": comment, "revision_comment": comment}
    if internal_comment:
        payload["internal_comment"] = internal_comment
    if duplicate_override:
        payload["duplicate_override"] = True
    if moderator is not None:
        payload.update(_comment_author_payload(moderator))
    try:
        return cards_client().post(
            f"/internal/cards/{card_id}/transition/",
            json=payload,
        )
    except ServiceClientError as exc:
        detail = (exc.payload or {}).get("detail") or str(exc)
        raise ModerationActionError(detail) from exc


def approve_card(card, moderator, comment=""):
    if card.get("status") not in CARD_REVIEW_STATUSES:
        raise ModerationActionError("Одобрить можно только заявку на модерации.")
    updated = transition(card["id"], CardStatus.ACTIVE, comment, duplicate_override=True, moderator=moderator)
    log_moderation_action(updated, moderator, "approve", comment)
    enqueue_event("moderation.decision_created", "moderation", card["id"], {"action": "approve", "card_id": card["id"]})
    return updated


def reject_card(card, moderator, comment):
    if not comment:
        raise ModerationActionError("Комментарий обязателен при отклонении.")
    if card.get("status") not in CARD_REVIEW_STATUSES:
        raise ModerationActionError("Отклонить можно только заявку на модерации.")
    updated = transition(card["id"], CardStatus.REJECTED, comment, moderator=moderator)
    log_moderation_action(updated, moderator, "reject", comment)
    enqueue_event("moderation.decision_created", "moderation", card["id"], {"action": "reject", "card_id": card["id"]})
    return updated


def request_card_revision(card, moderator, comment, internal_comment=""):
    if not comment:
        raise ModerationActionError("Комментарий обязателен при отправке на доработку.")
    if card.get("status") not in CARD_REVIEW_STATUSES:
        raise ModerationActionError("На доработку можно отправить только заявку на модерации.")
    updated = transition(
        card["id"],
        CardStatus.REVISION_REQUIRED,
        comment,
        moderator=moderator,
        internal_comment=internal_comment,
    )
    log_moderation_action(updated, moderator, "request_revision", comment)
    if internal_comment:
        log_moderation_action(updated, moderator, "internal_comment", internal_comment)
    enqueue_event(
        "moderation.decision_created",
        "moderation",
        card["id"],
        {"action": "request_revision", "card_id": card["id"]},
    )
    return updated

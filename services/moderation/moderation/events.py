from ekomek_common.constants import CardStatus, UserStatus

from .review_cases import open_card_review, open_user_review


def handle_user_registered(payload):
    open_user_review(payload)


def handle_user_manual_review_required(payload):
    payload = {**payload, "status": payload.get("status") or UserStatus.MANUAL_REVIEW}
    open_user_review(payload)


def handle_user_status_changed(payload):
    if payload.get("status") == UserStatus.MANUAL_REVIEW:
        open_user_review(payload)


def handle_card_submitted(payload):
    open_card_review(payload)


def handle_card_manual_review_required(payload):
    open_card_review(payload)


def handle_card_duplicate_detected(payload):
    open_card_review(
        {
            **payload,
            "status": payload.get("status") or CardStatus.MANUAL_REVIEW,
            "needs_extra_review": True,
        }
    )


def handle_card_status_changed(payload):
    if payload.get("status") == CardStatus.MANUAL_REVIEW:
        open_card_review(payload)


EVENT_HANDLERS = {
    "user.registered": handle_user_registered,
    "user.manual_review_required": handle_user_manual_review_required,
    "user.status_changed": handle_user_status_changed,
    "card.submitted": handle_card_submitted,
    "card.manual_review_required": handle_card_manual_review_required,
    "card.duplicate_detected": handle_card_duplicate_detected,
    "card.status_changed": handle_card_status_changed,
}

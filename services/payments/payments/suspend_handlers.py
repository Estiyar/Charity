from django.db import transaction

from ekomek_common.http import ServiceClientError, cards_client

from .models import Donation, PaymentStatus
from .payment_flow import TERMINAL_STATUSES, _apply_failure, append_payment_event
from .redistribution import handle_card_status_changed


def _fetch_card_status(card_id):
    try:
        payload = cards_client().get(f"/internal/cards/{card_id}/")
    except ServiceClientError:
        return None
    return payload.get("status") if payload else None


def cancel_open_donations_for_card(card_id, reason):
    donations = Donation.objects.filter(
        card_id=card_id,
        payment_status__in=[PaymentStatus.PENDING, PaymentStatus.PROCESSING],
    )
    for donation in donations:
        _apply_failure(donation, PaymentStatus.CANCELED, reason)
        append_payment_event(
            donation,
            "card_suspended",
            {"card_id": card_id, "reason": reason},
        )


@transaction.atomic
def handle_card_suspended(payload):
    card_id = payload.get("card_id")
    if not card_id:
        return
    reason = payload.get("reason") or "Сбор приостановлен"
    cancel_open_donations_for_card(card_id, reason)


def handle_card_status_changed_with_suspend(payload):
    handle_card_status_changed(payload)
    if payload.get("status") == "suspended":
        handle_card_suspended(payload)


def card_allows_payment(card_id):
    status = _fetch_card_status(card_id)
    return status == "active"

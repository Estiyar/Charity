from ekomek_common.constants import CardStatus, InvalidStatusTransition, POST_ACTIVATION_STATUSES

from .history_services import record_card_event, request_remoderation
from .models import FundraisingCard
from .services import collect_amount, refresh_escrow_from_expenses, set_escrow_totals, transition_card


def on_expense_totals_changed(payload):
    set_escrow_totals(
        payload["card_id"],
        payload.get("spent", 0),
        payload.get("pending", 0),
    )


def on_expense_approved(payload):
    card = FundraisingCard.objects.filter(pk=payload.get("card_id")).first()
    if card is None:
        return
    refresh_escrow_from_expenses(card)


def on_payment_succeeded(payload):
    collect_amount(
        payload["card_id"],
        payload["amount"],
        idempotency_key=f"payment:{payload['donation_id']}",
    )


def on_document_uploaded(payload):
    card = FundraisingCard.objects.filter(pk=payload.get("card_id")).first()
    if card is None:
        return
    event_type = "document_replaced" if payload.get("replaced") else "document_added"
    record_card_event(card, event_type, payload={"document_id": payload.get("document_id")})
    request_remoderation(card, ["critical_change:documents"])


def on_document_expired(payload):
    card = FundraisingCard.objects.filter(pk=payload.get("card_id")).first()
    if card is None or card.status not in POST_ACTIVATION_STATUSES:
        return
    card.moderation_verified_at = None
    card.save(update_fields=["moderation_verified_at", "updated_at"])
    if card.status == CardStatus.ACTIVE:
        try:
            transition_card(card, CardStatus.REVISION_REQUIRED, comment="Истёк срок медицинского документа")
            return
        except InvalidStatusTransition:
            pass
    request_remoderation(card, ["expired_document"])


EVENT_HANDLERS = {
    "expense.approved": on_expense_approved,
    "expense.totals_changed": on_expense_totals_changed,
    "payout.succeeded": on_expense_approved,
    "payment.succeeded": on_payment_succeeded,
    "document.uploaded": on_document_uploaded,
    "document.expired": on_document_expired,
}

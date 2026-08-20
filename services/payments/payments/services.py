from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.utils import timezone

from ekomek_common.constants import CardStatus
from ekomek_common.http import ServiceClientError, admin_client, cards_client
from ekomek_common.outbox import enqueue_event

from .models import Donation, PaymentStatus, RefundChoice, RefundDecision, RefundDecisionStatus


OWN_FUNDRAISER_DONATION_MESSAGE = "Нельзя жертвовать в собственный сбор."
DONOR_REFUND_DISABLED_MESSAGE = "Возврат донорам отключён."
PUBLIC_REDISTRIBUTION_CHOICES = (
    RefundChoice.KEEP,
    RefundChoice.HOLD,
    RefundChoice.REDIRECT,
)
PUBLIC_REDISTRIBUTION_OPTIONS = (
    {"value": RefundChoice.KEEP, "label": "Оставить семье получателя"},
    {"value": RefundChoice.HOLD, "label": "Оставить на текущей карточке до завершения проверки"},
    {"value": RefundChoice.REDIRECT, "label": "Перенаправить на другой активный сбор"},
)


class RefundDecisionError(Exception):
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(message)


def fetch_card(card_id):
    try:
        return cards_client().get(f"/internal/cards/{card_id}/")
    except ServiceClientError:
        return None


def list_active_cards(exclude_id=None):
    try:
        cards = cards_client().get("/internal/cards/", params={"status": CardStatus.ACTIVE})
    except ServiceClientError:
        return []
    if exclude_id:
        cards = [card for card in cards if card["id"] != exclude_id]
    return cards


def is_own_fundraiser(user, card):
    if not getattr(user, "is_authenticated", False):
        return False
    if card.get("author_id") == user.id:
        return True
    if user.iin_hash and card.get("iin_hash") and user.iin_hash == card["iin_hash"]:
        return True
    return False


def platform_settings():
    try:
        return admin_client().get("/internal/settings/")
    except ServiceClientError:
        return {"refund_commission_percent": 10, "refund_deadline_days": 7}


def calculate_refund_payout(share_amount, commission_percent):
    commission = (share_amount * Decimal(commission_percent) / Decimal("100")).quantize(Decimal("0.01"))
    return share_amount - commission, commission


def get_redirect_candidates(source_card):
    active = list_active_cards(exclude_id=source_card["id"])
    same = [card for card in active if card.get("diagnosis") == source_card.get("diagnosis")]
    return same or active


def validate_redirect_target(source_card, target_card):
    if target_card is None:
        raise RefundDecisionError("Укажите целевой сбор для перенаправления.", field="target_card_id")
    if target_card["id"] == source_card["id"]:
        raise RefundDecisionError("Нельзя перенаправить средства на тот же сбор.", field="target_card_id")
    if target_card.get("status") != CardStatus.ACTIVE:
        raise RefundDecisionError("Целевой сбор должен быть активным.", field="target_card_id")
    allowed_ids = {card["id"] for card in get_redirect_candidates(source_card)}
    if target_card["id"] not in allowed_ids:
        raise RefundDecisionError("Целевой сбор недоступен для перенаправления.", field="target_card_id")


def allocate_donation_shares(donations, leftover, collected_amount):
    donation_list = list(donations)
    if not donation_list or collected_amount <= 0 or leftover <= 0:
        return []
    allocated = Decimal("0")
    shares = []
    for index, donation in enumerate(donation_list):
        if index == len(donation_list) - 1:
            share = leftover - allocated
        else:
            share = (donation.amount / collected_amount * leftover).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            allocated += share
        if share > 0:
            shares.append((donation, share))
    return shares

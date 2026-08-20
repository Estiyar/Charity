from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ekomek_common.constants import CardStatus
from ekomek_common.http import ServiceClientError, cards_client
from ekomek_common.outbox import enqueue_event

from .models import Donation, PaymentStatus, RefundChoice, RefundDecision, RefundDecisionStatus
from .services import (
    DONOR_REFUND_DISABLED_MESSAGE,
    PUBLIC_REDISTRIBUTION_CHOICES,
    RefundDecisionError,
    allocate_donation_shares,
    fetch_card,
    platform_settings,
    validate_redirect_target,
)


def transition_remote_card(card_id, status_value):
    return cards_client().post(
        f"/internal/cards/{card_id}/transition/",
        json={"status": status_value},
    )


def collect_remote_card(card_id, amount, idempotency_key):
    return cards_client().post(
        f"/internal/cards/{card_id}/collect/",
        json={"amount": str(amount), "idempotency_key": idempotency_key},
    )


def maybe_open_redistribution_period(card):
    if card.get("status") != CardStatus.DECEASED:
        return
    if RefundDecision.objects.filter(card_id=card["id"]).exists():
        return
    leftover = Decimal(str(card.get("escrow_balance") if card.get("escrow_balance") is not None else card.get("collected_amount") or 0))
    collected = Decimal(str(card.get("collected_amount") or 0))
    if leftover <= 0:
        try:
            transition_remote_card(card["id"], CardStatus.ARCHIVED)
        except ServiceClientError:
            return
        return
    try:
        updated = transition_remote_card(card["id"], CardStatus.REDISTRIBUTION)
    except ServiceClientError:
        return
    card = updated or card
    settings = platform_settings()
    deadline = timezone.now() + timedelta(days=int(settings.get("refund_deadline_days", 7)))
    donations = Donation.objects.filter(card_id=card["id"], payment_status=PaymentStatus.SUCCESS).order_by("id")
    shares = allocate_donation_shares(donations, leftover, collected)
    for donation, share_amount in shares:
        if not donation.donor_id:
            continue
        RefundDecision.objects.create(
            donation=donation,
            card_id=card["id"],
            card_snapshot={
                "id": card["id"],
                "full_name": card.get("full_name"),
                "diagnosis": card.get("diagnosis"),
                "city": card.get("city"),
                "status": CardStatus.REDISTRIBUTION,
            },
            donor_id=donation.donor_id,
            share_amount=share_amount,
            deadline=deadline,
        )
    enqueue_event("redistribution.opened", "card", card["id"], {"card_id": card["id"]})


maybe_open_refund_period = maybe_open_redistribution_period


@transaction.atomic
def apply_redistribution_choice(decision, choice, target_card=None):
    if decision.status != RefundDecisionStatus.PENDING:
        raise RefundDecisionError("Решение уже принято.")
    if timezone.now() > decision.deadline:
        raise RefundDecisionError("Срок принятия решения истёк.")
    if choice == RefundChoice.REFUND:
        raise RefundDecisionError(DONOR_REFUND_DISABLED_MESSAGE, field="choice")
    if choice not in PUBLIC_REDISTRIBUTION_CHOICES:
        raise RefundDecisionError("Недопустимый вариант распределения.", field="choice")
    source_card = fetch_card(decision.card_id) or decision.card_snapshot
    share_amount = decision.share_amount
    if choice == RefundChoice.REDIRECT:
        validate_redirect_target(source_card, target_card)
        collect_remote_card(decision.card_id, -share_amount, f"redistribution:{decision.id}:debit")
        collect_remote_card(target_card["id"], share_amount, f"redistribution:{decision.id}:credit")
        decision.target_card_id = target_card["id"]
        decision.target_card_snapshot = target_card
    decision.choice = choice
    decision.status = RefundDecisionStatus.DONE
    decision.resolved_at = timezone.now()
    decision.save()
    enqueue_event(
        "redistribution.choice_applied",
        "card",
        decision.card_id,
        {
            "decision_id": decision.id,
            "choice": choice,
            "card_id": decision.card_id,
            "amount": str(share_amount),
            "target_card_id": decision.target_card_id,
        },
    )
    maybe_archive_card_after_decisions(decision.card_id)
    return decision


apply_refund_choice = apply_redistribution_choice


def expire_decision_as_keep(decision):
    if decision.status != RefundDecisionStatus.PENDING:
        return False
    if timezone.now() <= decision.deadline:
        return False
    decision.choice = RefundChoice.KEEP
    decision.status = RefundDecisionStatus.EXPIRED
    decision.resolved_at = timezone.now()
    decision.save(update_fields=["choice", "status", "resolved_at"])
    return True


def card_decisions_are_final(card_id):
    decisions = RefundDecision.objects.filter(card_id=card_id)
    if not decisions.exists():
        return False
    return not decisions.filter(status=RefundDecisionStatus.PENDING).exists()


def maybe_archive_card_after_decisions(card_id):
    if not card_decisions_are_final(card_id):
        return
    if RefundDecision.objects.filter(card_id=card_id, choice=RefundChoice.HOLD).exists():
        return
    try:
        transition_remote_card(card_id, CardStatus.ARCHIVED)
    except ServiceClientError:
        return


def process_expired_redistribution_deadlines():
    pending = RefundDecision.objects.filter(
        status=RefundDecisionStatus.PENDING,
        deadline__lt=timezone.now(),
    ).order_by("id")
    expired_count = 0
    affected = set()
    for decision in pending:
        if expire_decision_as_keep(decision):
            expired_count += 1
            affected.add(decision.card_id)
    for card_id in affected:
        maybe_archive_card_after_decisions(card_id)
    return expired_count, len(affected)


def handle_card_status_changed(payload):
    if payload.get("status") != CardStatus.DECEASED:
        return
    card = fetch_card(payload["card_id"])
    if card:
        maybe_open_redistribution_period(card)

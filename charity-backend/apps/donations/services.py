from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus, InvalidStatusTransition, transition
from apps.users.models import PlatformSettings
from apps.users.services import credit_user_balance

from .models import PaymentStatus, RefundChoice, RefundDecision, RefundDecisionStatus


class RefundDecisionError(Exception):
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(message)


REFUND_TRIGGER_STATUSES = {
    CardStatus.COMPLETED,
    CardStatus.DECEASED,
}

OWN_FUNDRAISER_DONATION_MESSAGE = "Нельзя жертвовать в собственный сбор."


def is_own_fundraiser(user, card):
    if not user.is_authenticated:
        return False
    if card.author_id == user.id:
        return True
    if user.iin and card.recipient_iin and user.iin == card.recipient_iin:
        return True
    return False


def calculate_leftover(card):
    return Decimal(str(card.collected_amount)) - Decimal(str(card.escrow_spent))


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
            share = (
                donation.amount / collected_amount * leftover
            ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            allocated += share
        if share > 0:
            shares.append((donation, share))
    return shares


def get_redirect_candidates(source_card):
    active_cards = FundraisingCard.objects.filter(
        status=CardStatus.ACTIVE,
    ).exclude(pk=source_card.pk).order_by("-created_at")
    same_diagnosis = active_cards.filter(diagnosis=source_card.diagnosis)
    if same_diagnosis.exists():
        return same_diagnosis
    return active_cards


def validate_redirect_target(source_card, target_card):
    if target_card is None:
        raise RefundDecisionError(
            "Укажите целевой сбор для перенаправления.",
            field="target_card_id",
        )
    if target_card.pk == source_card.pk:
        raise RefundDecisionError(
            "Нельзя перенаправить средства на тот же сбор.",
            field="target_card_id",
        )
    if target_card.status != CardStatus.ACTIVE:
        raise RefundDecisionError(
            "Целевой сбор должен быть активным.",
            field="target_card_id",
        )
    allowed_ids = set(
        get_redirect_candidates(source_card).values_list("pk", flat=True)
    )
    if target_card.pk not in allowed_ids:
        raise RefundDecisionError(
            "Целевой сбор недоступен для перенаправления.",
            field="target_card_id",
        )


def calculate_refund_payout(share_amount, commission_percent):
    commission = (
        share_amount * Decimal(commission_percent) / Decimal("100")
    ).quantize(Decimal("0.01"))
    payout = share_amount - commission
    return payout, commission


@transaction.atomic
def maybe_open_refund_period(card):
    if card.status not in REFUND_TRIGGER_STATUSES:
        return card
    if RefundDecision.objects.filter(card=card).exists():
        return card

    leftover = calculate_leftover(card)
    if leftover <= 0:
        return card

    try:
        transition(card, CardStatus.REDISTRIBUTION)
    except InvalidStatusTransition:
        if card.status != CardStatus.REDISTRIBUTION:
            raise

    settings = PlatformSettings.get_solo()
    deadline = timezone.now() + timedelta(days=settings.refund_deadline_days)
    donations = card.donations.filter(payment_status=PaymentStatus.SUCCESS).order_by(
        "id"
    )
    shares = allocate_donation_shares(
        donations,
        leftover,
        Decimal(str(card.collected_amount)),
    )

    for donation, share_amount in shares:
        if not donation.donor_id:
            continue
        RefundDecision.objects.create(
            donation=donation,
            card=card,
            donor=donation.donor,
            share_amount=share_amount,
            deadline=deadline,
        )

    return card


def handle_card_status_change(card, new_status):
    if new_status in REFUND_TRIGGER_STATUSES:
        maybe_open_refund_period(card)


@transaction.atomic
def apply_refund_choice(decision, choice, target_card=None):
    if decision.status != RefundDecisionStatus.PENDING:
        raise RefundDecisionError("Решение уже принято.")
    if timezone.now() > decision.deadline:
        raise RefundDecisionError("Срок принятия решения истёк.")

    if choice not in {
        RefundChoice.KEEP,
        RefundChoice.REFUND,
        RefundChoice.REDIRECT,
    }:
        raise RefundDecisionError("Недопустимый вариант распределения.", field="choice")

    source_card = decision.card
    share_amount = decision.share_amount
    settings = PlatformSettings.get_solo()

    if choice == RefundChoice.KEEP:
        pass
    elif choice == RefundChoice.REFUND:
        FundraisingCard.objects.filter(pk=source_card.pk).update(
            collected_amount=F("collected_amount") - share_amount
        )
        payout, _commission = calculate_refund_payout(
            share_amount,
            settings.refund_commission_percent,
        )
        credit_user_balance(
            decision.donor,
            payout,
            description=f"Возврат по сбору «{source_card.full_name}»",
        )
    elif choice == RefundChoice.REDIRECT:
        validate_redirect_target(source_card, target_card)
        FundraisingCard.objects.filter(pk=source_card.pk).update(
            collected_amount=F("collected_amount") - share_amount
        )
        FundraisingCard.objects.filter(pk=target_card.pk).update(
            collected_amount=F("collected_amount") + share_amount
        )
        decision.target_card = target_card

    decision.choice = choice
    decision.status = RefundDecisionStatus.DONE
    decision.resolved_at = timezone.now()
    decision.save(
        update_fields=[
            "choice",
            "status",
            "target_card",
            "resolved_at",
        ]
    )
    maybe_archive_card_after_refunds(decision.card)
    return decision


def expire_refund_decision_as_keep(decision):
    if decision.status != RefundDecisionStatus.PENDING:
        return False
    if timezone.now() <= decision.deadline:
        return False
    decision.choice = RefundChoice.KEEP
    decision.status = RefundDecisionStatus.EXPIRED
    decision.resolved_at = timezone.now()
    decision.save(update_fields=["choice", "status", "resolved_at"])
    return True


def card_refund_decisions_are_final(card):
    decisions = RefundDecision.objects.filter(card=card)
    if not decisions.exists():
        return False
    return not decisions.filter(status=RefundDecisionStatus.PENDING).exists()


def maybe_archive_card_after_refunds(card):
    card = FundraisingCard.objects.get(pk=card.pk)
    if card.status != CardStatus.REDISTRIBUTION:
        return card
    if not card_refund_decisions_are_final(card):
        return card
    transition(card, CardStatus.ARCHIVED)
    return card


@transaction.atomic
def process_expired_refund_deadlines():
    pending_decisions = (
        RefundDecision.objects.filter(
            status=RefundDecisionStatus.PENDING,
            deadline__lt=timezone.now(),
        )
        .select_related("card")
        .order_by("id")
    )
    affected_card_ids = set()
    expired_count = 0
    for decision in pending_decisions:
        if expire_refund_decision_as_keep(decision):
            expired_count += 1
            affected_card_ids.add(decision.card_id)

    archived_count = 0
    for card_id in affected_card_ids:
        card = FundraisingCard.objects.get(pk=card_id)
        previous_status = card.status
        maybe_archive_card_after_refunds(card)
        card.refresh_from_db()
        if previous_status != card.status and card.status == CardStatus.ARCHIVED:
            archived_count += 1

    return expired_count, archived_count

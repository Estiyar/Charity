from datetime import timedelta

from django.utils import timezone

from ekomek_common.constants import CardStatus, InvalidStatusTransition
from ekomek_common.http import ServiceClientError, admin_client

from .models import FundraisingCard
from .repositories import CardRepository


class BusinessLimitViolation(Exception):
    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(message)


def _fetch_limits():
    from ekomek_common.risk import DEFAULT_BUSINESS_LIMITS
    try:
        config = admin_client().get("/internal/risk-config/")
        merged = dict(DEFAULT_BUSINESS_LIMITS)
        merged.update((config or {}).get("business_limits") or {})
        return merged
    except ServiceClientError:
        return dict(DEFAULT_BUSINESS_LIMITS)


def check_fundraiser_creation_frequency(author_id):
    limits = _fetch_limits()
    max_per_month = limits.get("max_fundraisers_per_author_per_month", 2)
    max_active = limits.get("max_fundraisers_per_author_total_active", 1)

    month_ago = timezone.now() - timedelta(days=30)
    recent_count = FundraisingCard.objects.filter(
        author_id=author_id, created_at__gte=month_ago
    ).count()
    if recent_count >= max_per_month:
        raise BusinessLimitViolation(
            f"Превышен лимит создания сборов: максимум {max_per_month} за 30 дней.",
            field="non_field_errors",
        )

    active_count = FundraisingCard.objects.filter(
        author_id=author_id,
        status__in=[CardStatus.ACTIVE, CardStatus.PENDING_MODERATION, CardStatus.MANUAL_REVIEW],
    ).count()
    if active_count >= max_active:
        raise BusinessLimitViolation(
            f"У вас уже есть активный сбор. Максимум: {max_active}.",
            field="non_field_errors",
        )


def check_beneficiary_change_allowed(card):
    limits = _fetch_limits()
    if limits.get("beneficiary_change_after_activation_forbidden", True):
        from ekomek_common.constants import POST_ACTIVATION_STATUSES
        if card.status in POST_ACTIVATION_STATUSES:
            raise BusinessLimitViolation(
                "Смена получателя после активации запрещена.",
                field="beneficiary_id",
            )


def check_target_amount_change(card, new_amount):
    if card.status == CardStatus.ACTIVE and new_amount != card.target_amount:
        return True
    return False


def check_clinic_change(card, new_clinic):
    if card.status == CardStatus.ACTIVE and new_clinic != card.clinic:
        return True
    return False


def check_payout_change(card, new_hash):
    if not new_hash or not card.payout_details_hash:
        return False
    if card.status == CardStatus.ACTIVE and new_hash != card.payout_details_hash:
        return True
    return False


def check_conflicting_document_uploads(card_id):
    limits = _fetch_limits()
    threshold = limits.get("conflicting_document_uploads_threshold", 3)
    from .models import CardHistoryEvent
    recent = CardHistoryEvent.objects.filter(
        card_id=card_id,
        event_type__in=["document_added", "document_replaced"],
        created_at__gte=timezone.now() - timedelta(days=7),
    ).count()
    return recent >= threshold

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from ekomek_common.constants import (
    CardStatus,
    InvalidStatusTransition,
    RelationshipType,
    RepresentationStatus,
    next_status,
)
from ekomek_common.crypto import hmac_hash, protect_document_number, protect_identifier, protect_phone
from ekomek_common.http import ServiceClientError, expenses_client, profile_client, verification_client
from ekomek_common.outbox import enqueue_event

from .catalog_cache import invalidate_catalog_cache
from .duplicate_services import apply_duplicate_check
from .models import CollectionReceipt, FundraisingCard
from .recipient_cache import consume_recipient_session
from .repositories import CardRepository


class FundraiserCreationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(errors)


def _fetch_fraud(*, iin=None, iin_hash=None):
    try:
        if iin_hash:
            return verification_client().get(f"/internal/antifraud/hash/{iin_hash}/")
        return verification_client().post("/internal/antifraud/lookup/", json={"iin": iin})
    except ServiceClientError as exc:
        if exc.status_code == 404:
            return None
        return None


def check_blocked_iin(*, iin=None, iin_hash=None, field_name):
    profile = _fetch_fraud(iin=iin, iin_hash=iin_hash)
    if profile and profile.get("blocked"):
        return {field_name: "Высокий уровень риска. Создание сбора невозможно."}
    return None


def apply_beneficiary_snapshot(validated_data, session):
    snapshot = session["snapshot"]
    iin = session["iin"]
    protected = protect_identifier(iin)
    for field in ("full_name", "city", "clinic", "diagnosis", "gender", "age"):
        if snapshot.get(field) not in (None, ""):
            validated_data[field] = snapshot[field]
    validated_data["is_self"] = bool(snapshot.get("is_self") or session["relationship_type"] == RelationshipType.SELF)
    validated_data["iin_hash"] = protected["hash"]
    validated_data["iin_masked"] = protected["masked"]
    validated_data["iin_encrypted"] = protected["encrypted"]
    validated_data["beneficiary_id"] = session["beneficiary_id"]
    validated_data["representation_id"] = session["representation_id"]
    validated_data["relationship_type"] = session["relationship_type"]
    validated_data["high_risk"] = bool(snapshot.get("high_risk") or snapshot.get("requires_manual_review"))
    validated_data["review_reasons"] = snapshot.get("review_reasons") or []
    validated_data["medical_source"] = snapshot.get("source") or ""
    validated_data["needs_extra_review"] = bool(
        snapshot.get("needs_review")
        or snapshot.get("requires_manual_review")
        or snapshot.get("incomplete")
        or snapshot.get("high_risk")
    )
    if snapshot.get("source") == "official":
        checked_at = timezone.now()
        if snapshot.get("diagnosis"):
            validated_data["diagnosis_verified_at"] = checked_at
        if snapshot.get("clinic"):
            validated_data["clinic_verified_at"] = checked_at
    return validated_data


def apply_protected_contacts(validated_data):
    document_number = validated_data.pop("document_number", None)
    contact_phone = validated_data.pop("contact_phone", None)
    if document_number:
        protected = protect_document_number(document_number)
        validated_data["document_number_hash"] = protected["hash"]
        validated_data["document_number_masked"] = protected["masked"]
        validated_data["document_number_encrypted"] = protected["encrypted"]
    if contact_phone:
        protected = protect_phone(contact_phone)
        validated_data["contact_phone_encrypted"] = protected["encrypted"]
        validated_data["contact_phone_masked"] = protected["masked"]
    return validated_data


def prepare_fundraiser_data(author, validated_data):
    if not getattr(author, "can_create_public_fundraiser", True):
        raise FundraiserCreationError(
            {"non_field_errors": ["Создание публичного сбора недоступно до завершения проверки ЭЦП."]}
        )
    session = consume_recipient_session(validated_data.pop("recipient_session_token", None))
    if session is None:
        raise FundraiserCreationError(
            {"recipient_session_token": "Сначала подтвердите получателя через ЭЦП или официальный источник."}
        )
    iin = session["iin"]
    repository = CardRepository()
    errors = {}
    author_iin_hash = getattr(author, "iin_hash", "") or ""
    if author_iin_hash:
        author_error = check_blocked_iin(iin_hash=author_iin_hash, field_name="author_iin")
        if author_error:
            errors.update(author_error)
    recipient_error = check_blocked_iin(iin=iin, field_name="beneficiary")
    if recipient_error:
        errors.update(recipient_error)
    if repository.author_has_active(author.id):
        errors["non_field_errors"] = ["У вас уже есть активный сбор."]
    if repository.recipient_has_active(hmac_hash(iin)):
        errors["beneficiary"] = "У получателя уже есть активный сбор."
    if errors:
        raise FundraiserCreationError(errors)
    validated_data.pop("recipient_iin", None)
    validated_data.pop("iin", None)
    return apply_protected_contacts(apply_beneficiary_snapshot(validated_data, session))


def requires_manual_review(card):
    return bool(card.high_risk or card.needs_extra_review or card.duplicate_suspected)


def submit_target_status(card):
    if requires_manual_review(card):
        return CardStatus.MANUAL_REVIEW
    return CardStatus.PENDING_MODERATION


def submit_card_for_moderation(card, request=None):
    apply_duplicate_check(card, request=request)
    from .risk_engine import calculate_risk_score, should_auto_suspend, should_trigger_manual_review

    assessment = calculate_risk_score(card)
    card.refresh_from_db()
    if should_trigger_manual_review(assessment):
        card.needs_extra_review = True
        card.save(update_fields=["needs_extra_review", "updated_at"])
    transition_card(card, submit_target_status(card))
    enqueue_event(
        "card.submitted",
        "card",
        card.id,
        {
            "card_id": card.id,
            "status": card.status,
            "high_risk": card.high_risk,
            "needs_extra_review": card.needs_extra_review,
            "review_reasons": card.review_reasons,
            "iin_hash": card.iin_hash,
        },
    )
    if requires_manual_review(card):
        enqueue_event(
            "card.manual_review_required",
            "card",
            card.id,
            {"card_id": card.id, "reasons": card.review_reasons, "iin_hash": card.iin_hash},
        )
    return card


def create_card(author, validated_data):
    validated_data["author_id"] = author.id
    validated_data["author_email"] = author.email
    validated_data["author_full_name"] = author.full_name
    card = FundraisingCard.objects.create(**validated_data)
    enqueue_event("card.created", "card", card.id, {"card_id": card.id, "author_id": author.id})
    from .history_services import record_card_event

    record_card_event(card, "card_created", actor=author)
    if card.needs_extra_review or card.high_risk:
        enqueue_event(
            "card.manual_review_required",
            "card",
            card.id,
            {"card_id": card.id, "reasons": card.review_reasons},
        )
    return card


def representation_allows_active(card):
    if card.is_self or card.relationship_type == RelationshipType.SELF:
        return True
    if not card.representation_id:
        return False
    try:
        payload = profile_client().get(f"/internal/representations/{card.representation_id}/")
    except ServiceClientError:
        return False
    return payload.get("verification_status") == RepresentationStatus.VERIFIED


def transition_card(card, target, save=True, actor=None, comment=""):
    if target == CardStatus.ACTIVE and not representation_allows_active(card):
        raise InvalidStatusTransition(
            "Сбор для другого получателя нельзя активировать без подтверждённого представительства."
        )
    if target == CardStatus.ACTIVE and card.duplicate_suspected and not card.duplicate_override:
        raise InvalidStatusTransition(
            "Карточка с признаками дубля не может быть опубликована без решения модератора."
        )
    previous = card.status
    next_status(card.status, target)
    card.status = target
    update_fields = ["status", "updated_at"]
    if target == CardStatus.ACTIVE:
        card.moderation_verified_at = timezone.now()
        update_fields.append("moderation_verified_at")
    if save:
        card.save(update_fields=update_fields)
    from .history_services import record_status_change

    record_status_change(card, previous, target, actor=actor, comment=comment)
    enqueue_event(
        "card.status_changed",
        "card",
        card.id,
        {"card_id": card.id, "status": card.status, "previous_status": previous},
    )
    if target == CardStatus.SUSPENDED:
        enqueue_event(
            "card.suspended",
            "card",
            card.id,
            {
                "card_id": card.id,
                "reason": comment or card.suspend_reason,
                "previous_status": previous,
                "author_id": card.author_id,
            },
        )
    elif previous == CardStatus.SUSPENDED and target != CardStatus.SUSPENDED:
        enqueue_event(
            "card.unsuspended",
            "card",
            card.id,
            {
                "card_id": card.id,
                "reason": comment,
                "restored_status": target,
                "author_id": card.author_id,
            },
        )
    if target == CardStatus.REVISION_REQUIRED:
        enqueue_event(
            "card.revision_required",
            "card",
            card.id,
            {
                "card_id": card.id,
                "author_id": card.author_id,
                "revision_comment": comment or card.moderator_comment,
                "status": card.status,
            },
        )
    return card


@transaction.atomic
def collect_amount(card_id, amount, idempotency_key=None):
    amount = Decimal(str(amount))
    card = FundraisingCard.objects.select_for_update().get(pk=card_id)
    if idempotency_key:
        try:
            with transaction.atomic():
                CollectionReceipt.objects.create(
                    card_id=card_id,
                    idempotency_key=idempotency_key,
                    amount=amount,
                )
        except IntegrityError:
            card.refresh_from_db()
            return card
    FundraisingCard.objects.filter(pk=card.pk).update(
        collected_amount=F("collected_amount") + amount
    )
    invalidate_catalog_cache()
    card.refresh_from_db()
    if card.status == CardStatus.ACTIVE and card.collected_amount >= card.target_amount:
        try:
            transition_card(card, CardStatus.COMPLETED)
        except InvalidStatusTransition:
            pass
    return card


def refresh_escrow_from_expenses(card):
    try:
        totals = expenses_client().get(f"/internal/cards/{card.id}/totals/")
    except ServiceClientError:
        return card
    card.escrow_spent = totals.get("spent") or 0
    card.escrow_pending = totals.get("pending") or 0
    card.save(update_fields=["escrow_spent", "escrow_pending", "updated_at"])
    return card


def set_escrow_totals(card_id, spent, pending):
    FundraisingCard.objects.filter(pk=card_id).update(
        escrow_spent=spent,
        escrow_pending=pending,
    )
    invalidate_catalog_cache()


def is_own_fundraiser(user, card):
    if not getattr(user, "is_authenticated", False):
        return False
    if card.author_id == user.id:
        return True
    user_hash = getattr(user, "iin_hash", "") or ""
    card_hash = getattr(card, "iin_hash", "") or ""
    if user_hash and card_hash and user_hash == card_hash:
        return True
    return False

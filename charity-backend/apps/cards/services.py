from apps.antifraud.services import is_blocked, needs_review
from apps.common.card_status import CardStatus
from apps.medregistry.services import (
    calculate_age_from_birth_date,
    fetch_medical_record,
    get_primary_diagnosis_name,
)

from .models import FundraisingCard


class FundraiserCreationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(errors)


ACTIVE_FUNDRAISER_STATUSES = {
    CardStatus.DRAFT,
    CardStatus.PENDING_MODERATION,
    CardStatus.REVISION_REQUIRED,
    CardStatus.APPROVED,
    CardStatus.ACTIVE,
}


def recipient_has_active_fundraiser(recipient_iin):
    return FundraisingCard.objects.filter(
        recipient_iin=recipient_iin,
        status__in=ACTIVE_FUNDRAISER_STATUSES,
    ).exists()


def author_has_active_fundraiser(author):
    if not author.iin:
        return FundraisingCard.objects.filter(
            author=author,
            status__in=ACTIVE_FUNDRAISER_STATUSES,
        ).exists()
    return FundraisingCard.objects.filter(
        author__iin=author.iin,
        status__in=ACTIVE_FUNDRAISER_STATUSES,
    ).exists()


def check_blocked_iin(iin, field_name):
    if is_blocked(iin):
        return {field_name: "Высокий уровень риска. Создание сбора невозможно."}
    return None


def should_flag_extra_review(author_iin, recipient_iin):
    if author_iin and needs_review(author_iin):
        return True
    return needs_review(recipient_iin)


def apply_medregistry_data(validated_data, record, author_iin, recipient_iin):
    validated_data["full_name"] = record.full_name
    validated_data["city"] = record.city
    validated_data["clinic"] = record.clinic
    validated_data["diagnosis"] = get_primary_diagnosis_name(record)
    validated_data["gender"] = record.gender
    validated_data["age"] = calculate_age_from_birth_date(record.birth_date)
    validated_data["recipient_iin"] = recipient_iin
    validated_data["is_self"] = bool(author_iin and author_iin == recipient_iin)
    validated_data["iin_encrypted"] = recipient_iin
    return validated_data


def prepare_fundraiser_data(author, validated_data):
    recipient_iin = validated_data.get("recipient_iin") or validated_data.pop("iin", None)
    if not recipient_iin:
        raise FundraiserCreationError(
            {"recipient_iin": "ИИН получателя обязателен."}
        )

    errors = {}
    if author.iin:
        author_error = check_blocked_iin(author.iin, "author_iin")
        if author_error:
            errors.update(author_error)

    recipient_error = check_blocked_iin(recipient_iin, "recipient_iin")
    if recipient_error:
        errors.update(recipient_error)

    if author_has_active_fundraiser(author):
        errors["non_field_errors"] = ["У вас уже есть активный сбор."]

    if recipient_has_active_fundraiser(recipient_iin):
        errors["recipient_iin"] = "У получателя уже есть активный сбор."

    record = fetch_medical_record(recipient_iin)
    if record is None:
        errors["recipient_iin"] = "Получатель не найден в медреестре."

    if errors:
        raise FundraiserCreationError(errors)

    validated_data = apply_medregistry_data(
        validated_data, record, author.iin, recipient_iin
    )
    validated_data["needs_extra_review"] = should_flag_extra_review(
        author.iin, recipient_iin
    )
    return validated_data

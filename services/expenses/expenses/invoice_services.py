from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ekomek_common.crypto import encrypt_value, hmac_hash
from ekomek_common.outbox import enqueue_event
from ekomek_common.validators import validate_upload

from .masking import mask_bin, mask_iban
from .payout_models import (
    Invoice,
    InvoiceDecisionEvent,
    InvoiceStatus,
    OrganizationKind,
    OrganizationStatus,
    OrganizationVerificationEvent,
    VerifiedOrganization,
)
from .receipts import build_public_receipt
from .workflow import ExpenseActionError, escrow_available, publish_totals


def record_invoice_decision(invoice, action, *, actor=None, reason=""):
    return InvoiceDecisionEvent.objects.create(
        invoice=invoice,
        action=action,
        reason=reason or "",
        actor_id=getattr(actor, "id", None),
        actor_role=getattr(actor, "role", "") or "",
    )


def record_org_verification(organization, action, *, actor=None, reason=""):
    return OrganizationVerificationEvent.objects.create(
        organization=organization,
        action=action,
        reason=reason or "",
        actor_id=getattr(actor, "id", None),
        actor_role=getattr(actor, "role", "") or "",
    )


def _normalized_bin(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) != 12:
        raise ExpenseActionError("БИН организации должен содержать 12 цифр.")
    return digits


def _normalized_iban(value):
    text = str(value or "").replace(" ", "").upper()
    if len(text) < 15:
        raise ExpenseActionError("Укажите корректный IBAN получателя.")
    return text


def get_or_create_payee(validated, *, actor=None):
    bin_value = _normalized_bin(validated["organization_bin"])
    iban = _normalized_iban(validated["iban"])
    bin_hash = hmac_hash(bin_value)
    organization = VerifiedOrganization.objects.filter(bin_hash=bin_hash).first()
    if organization:
        return organization
    return VerifiedOrganization.objects.create(
        name=validated["organization_name"].strip(),
        kind=validated.get("organization_kind") or OrganizationKind.CLINIC,
        bin_hash=bin_hash,
        bin_masked=mask_bin(bin_value),
        bin_encrypted=encrypt_value(bin_value),
        iban_masked=mask_iban(iban),
        iban_encrypted=encrypt_value(iban),
        bank_name=(validated.get("bank_name") or "").strip(),
        created_by_id=getattr(actor, "id", None),
    )


def _attach_invoice_file(invoice, uploaded):
    if uploaded is None:
        raise ExpenseActionError("Приложите счёт клиники или поставщика.")
    validate_upload(uploaded)
    invoice.file_name = uploaded.name
    invoice.original_file = uploaded
    uploaded.seek(0)
    file_bytes = uploaded.read()
    uploaded.seek(0)
    invoice.public_file.save(
        "invoice.png",
        build_public_receipt(invoice, file_bytes, uploaded.name, title="Счёт на прямую выплату"),
        save=False,
    )


@transaction.atomic
def create_invoice(card, validated, *, actor=None, uploaded=None):
    if Decimal(str(validated["amount"])) > escrow_available(card):
        raise ExpenseActionError("Сумма счёта превышает доступный эскроу-баланс.")
    organization = get_or_create_payee(validated, actor=actor)
    invoice = Invoice(
        card_id=card["id"],
        card_name=card.get("full_name", ""),
        organization=organization,
        number=(validated.get("number") or "").strip(),
        date=validated["date"],
        amount=validated["amount"],
        currency=(validated.get("currency") or "KZT").upper(),
        comment=validated.get("comment") or "",
        submitted_by_id=getattr(actor, "id", None),
        submitted_at=timezone.now(),
        status=InvoiceStatus.PENDING_VERIFICATION,
        publish_receipt=bool(validated.get("publish_receipt", True)),
    )
    _attach_invoice_file(invoice, uploaded)
    invoice.save()
    record_invoice_decision(invoice, "created", actor=actor)
    publish_totals(invoice.card_id)
    enqueue_event("invoice.created", "invoice", invoice.id, {"invoice_id": invoice.id, "card_id": invoice.card_id})
    return invoice


@transaction.atomic
def verify_invoice(invoice, comment="", *, actor=None, create_payout=True):
    from .payout_services import request_payout

    invoice = Invoice.objects.select_for_update().select_related("organization").get(pk=invoice.pk)
    if invoice.status != InvoiceStatus.PENDING_VERIFICATION:
        raise ExpenseActionError("Счёт уже обработан.")
    organization = VerifiedOrganization.objects.select_for_update().get(pk=invoice.organization_id)
    if organization.verification_status != OrganizationStatus.VERIFIED:
        organization.verification_status = OrganizationStatus.VERIFIED
        organization.verified_at = timezone.now()
        organization.verified_by_id = getattr(actor, "id", None)
        organization.verification_reason = comment or "Организация подтверждена."
        organization.save()
        record_org_verification(organization, "verified", actor=actor, reason=comment)
    invoice.status = InvoiceStatus.VERIFIED
    invoice.reviewed_at = timezone.now()
    invoice.reviewed_by_id = getattr(actor, "id", None)
    invoice.decision_reason = comment or ""
    invoice.save()
    record_invoice_decision(invoice, "verified", actor=actor, reason=comment)
    enqueue_event("invoice.verified", "invoice", invoice.id, {"invoice_id": invoice.id, "card_id": invoice.card_id})
    if create_payout:
        request_payout(invoice, actor=actor)
    publish_totals(invoice.card_id)
    return invoice


@transaction.atomic
def reject_invoice(invoice, comment, *, actor=None):
    if not comment:
        raise ExpenseActionError("Комментарий обязателен при отклонении счёта.")
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != InvoiceStatus.PENDING_VERIFICATION:
        raise ExpenseActionError("Счёт уже обработан.")
    invoice.status = InvoiceStatus.REJECTED
    invoice.reviewed_at = timezone.now()
    invoice.reviewed_by_id = getattr(actor, "id", None)
    invoice.decision_reason = comment
    invoice.save()
    record_invoice_decision(invoice, "rejected", actor=actor, reason=comment)
    enqueue_event(
        "invoice.rejected",
        "invoice",
        invoice.id,
        {"invoice_id": invoice.id, "card_id": invoice.card_id, "reason": comment},
    )
    publish_totals(invoice.card_id)
    return invoice


@transaction.atomic
def cancel_invoice(invoice, *, actor=None):
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != InvoiceStatus.PENDING_VERIFICATION:
        raise ExpenseActionError("Отменить можно только счёт на проверке.")
    invoice.status = InvoiceStatus.CANCELED
    invoice.save(update_fields=["status", "updated_at"])
    record_invoice_decision(invoice, "canceled", actor=actor)
    publish_totals(invoice.card_id)
    return invoice

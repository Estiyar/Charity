import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ekomek_common.http import ServiceClientError, cards_client
from ekomek_common.outbox import enqueue_event

from .models import Donation, LedgerEntry, LedgerEntryType, PaymentEvent, PaymentStatus, ProcessedProviderEvent
from .providers import get_payment_adapter
from .providers.exceptions import ProviderMismatchError
from .providers.types import ProviderResult


TERMINAL_STATUSES = {PaymentStatus.SUCCESS, PaymentStatus.FAILED, PaymentStatus.CANCELED}


class PaymentFlowError(Exception):
    def __init__(self, message, field=None, status_code=400):
        self.message = message
        self.field = field
        self.status_code = status_code
        super().__init__(message)


def as_decimal(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaymentFlowError("Некорректная сумма.") from exc


def append_payment_event(donation, event_type, payload=None):
    return PaymentEvent.objects.create(
        donation=donation,
        event_type=event_type,
        payload=payload or {},
    )


def payment_public_urls(donation):
    frontend = (getattr(settings, "PAYMENT_FRONTEND_URL", "") or "http://localhost:5173").rstrip("/")
    api = (getattr(settings, "PAYMENT_PUBLIC_API_URL", "") or "http://localhost:8080").rstrip("/")
    adapter_name = get_payment_adapter().name
    return {
        "success_url": f"{frontend}/payments/result?payment={donation.id}",
        "failure_url": f"{frontend}/payments/result?payment={donation.id}&outcome=failed",
        "result_url": f"{api}/api/payments/webhook/{adapter_name}",
    }


def resolve_idempotency_key(requested):
    key = (requested or "").strip()
    return key or uuid.uuid4().hex


@transaction.atomic
def create_payment_session(card, donor, data):
    amount = as_decimal(data["amount"])
    if amount < Decimal("1.00"):
        raise PaymentFlowError("Минимальная сумма пожертвования — 1 ₸.", field="amount")
    idempotency_key = resolve_idempotency_key(data.get("idempotency_key"))
    existing = Donation.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    donor_id = donor.id if donor and getattr(donor, "is_authenticated", False) else None
    donation = Donation.objects.create(
        card_id=card["id"],
        card_name=card.get("full_name", ""),
        donor_id=donor_id,
        donor_name=data["donor_name"],
        email=data.get("email") or "",
        phone=data.get("phone") or "",
        amount=amount,
        currency=getattr(settings, "PAYMENT_CURRENCY", "KZT"),
        payment_method=data.get("payment_method") or "",
        payment_status=PaymentStatus.PENDING,
        idempotency_key=idempotency_key,
    )
    adapter = get_payment_adapter()
    session = adapter.create_session(donation, payment_public_urls(donation))
    donation.provider = session.provider
    donation.provider_payment_id = session.provider_payment_id
    donation.redirect_url = session.redirect_url
    donation.payment_status = PaymentStatus.PROCESSING
    donation.save(
        update_fields=["provider", "provider_payment_id", "redirect_url", "payment_status", "updated_at"]
    )
    append_payment_event(
        donation,
        "created",
        {"provider": session.provider, "provider_payment_id": session.provider_payment_id},
    )
    enqueue_event(
        "payment.created",
        "payment",
        donation.id,
        {
            "donation_id": donation.id,
            "card_id": donation.card_id,
            "donor_id": donation.donor_id,
            "email": donation.email,
            "phone": donation.phone,
            "amount": str(donation.amount),
            "currency": donation.currency,
            "provider": donation.provider,
        },
    )
    return donation


def verify_result_against_donation(donation, result: ProviderResult):
    if str(result.order_id) != str(donation.id):
        raise ProviderMismatchError("order_id не совпадает с платежом.")
    if result.card_id != donation.card_id:
        raise ProviderMismatchError("card_id в уведомлении провайдера не совпадает.")
    if as_decimal(result.amount) != donation.amount:
        raise ProviderMismatchError("Сумма в уведомлении провайдера не совпадает.")
    if (result.currency or "").upper() != (donation.currency or "").upper():
        raise ProviderMismatchError("Валюта в уведомлении провайдера не совпадает.")
    if donation.provider_payment_id and result.provider_payment_id != donation.provider_payment_id:
        raise ProviderMismatchError("provider_payment_id не совпадает.")


def credit_card_collected(donation):
    try:
        cards_client().post(
            f"/internal/cards/{donation.card_id}/collect/",
            json={
                "amount": str(donation.amount),
                "idempotency_key": f"payment:{donation.id}",
            },
        )
    except ServiceClientError as exc:
        raise PaymentFlowError(
            "Не удалось обновить сумму сбора.",
            status_code=exc.status_code or 503,
        ) from exc


def _mark_processed(event):
    event.processed = True
    event.processed_at = timezone.now()
    event.save(update_fields=["processed", "processed_at"])


@transaction.atomic
def apply_provider_result(result: ProviderResult):
    donation = Donation.objects.select_for_update().filter(pk=result.order_id).first()
    if donation is None:
        raise PaymentFlowError("Платёж не найден.", status_code=404)
    verify_result_against_donation(donation, result)
    event, _created = ProcessedProviderEvent.objects.get_or_create(
        provider=result.provider,
        event_key=result.event_key or f"{result.provider_payment_id}:{result.status}",
        defaults={"payload": result.raw or {}},
    )
    event = ProcessedProviderEvent.objects.select_for_update().get(pk=event.pk)
    if event.processed:
        return donation
    append_payment_event(donation, "webhook_received", result.raw or {})
    if not donation.provider_payment_id:
        donation.provider_payment_id = result.provider_payment_id
    if result.status == "success":
        _apply_success(donation, result)
    elif result.status == "canceled":
        _apply_failure(donation, PaymentStatus.CANCELED, result.failed_reason or "Отменён")
    else:
        _apply_failure(donation, PaymentStatus.FAILED, result.failed_reason or "Оплата не прошла")
    _mark_processed(event)
    return donation


def _apply_success(donation, result):
    if donation.payment_status == PaymentStatus.SUCCESS and donation.collected_applied:
        return
    try:
        card = cards_client().get(f"/internal/cards/{donation.card_id}/")
    except ServiceClientError:
        card = None
    if card and card.get("status") != "active":
        _apply_failure(donation, PaymentStatus.CANCELED, "Сбор недоступен для пожертвований")
        return
    if donation.payment_status == PaymentStatus.SUCCESS:
        if not donation.collected_applied:
            credit_card_collected(donation)
            donation.collected_applied = True
            donation.save(update_fields=["collected_applied", "updated_at"])
        return
    donation.payment_status = PaymentStatus.SUCCESS
    donation.paid_at = timezone.now()
    donation.failed_reason = ""
    donation.save(update_fields=["payment_status", "paid_at", "failed_reason", "provider_payment_id", "updated_at"])
    LedgerEntry.objects.create(
        donation=donation,
        card_id=donation.card_id,
        amount=donation.amount,
        currency=donation.currency,
        entry_type=LedgerEntryType.DONATION_CREDIT,
    )
    credit_card_collected(donation)
    donation.collected_applied = True
    donation.save(update_fields=["collected_applied", "updated_at"])
    append_payment_event(donation, "succeeded", {"amount": str(donation.amount)})
    enqueue_event(
        "payment.succeeded",
        "payment",
        donation.id,
        {
            "donation_id": donation.id,
            "card_id": donation.card_id,
            "donor_id": donation.donor_id,
            "amount": str(donation.amount),
            "currency": donation.currency,
            "provider": donation.provider,
            "provider_payment_id": donation.provider_payment_id,
        },
    )


def _apply_failure(donation, status, reason):
    if donation.payment_status == PaymentStatus.SUCCESS:
        return
    donation.payment_status = status
    donation.failed_reason = reason
    donation.save(update_fields=["payment_status", "failed_reason", "provider_payment_id", "updated_at"])
    event_name = "canceled" if status == PaymentStatus.CANCELED else "failed"
    append_payment_event(donation, event_name, {"reason": reason})
    enqueue_event(
        "payment.failed",
        "payment",
        donation.id,
        {
            "donation_id": donation.id,
            "card_id": donation.card_id,
            "donor_id": donation.donor_id,
            "email": donation.email,
            "phone": donation.phone,
            "amount": str(donation.amount),
            "status": status,
            "reason": reason,
        },
    )


def apply_browser_outcome(donation, outcome):
    if outcome == "cancel" and donation.payment_status not in TERMINAL_STATUSES:
        _apply_failure(donation, PaymentStatus.CANCELED, "Отменено пользователем")
    return donation


def complete_dev_payment(donation, outcome):
    adapter = get_payment_adapter("dev")
    payload = {
        "order_id": str(donation.id),
        "provider_payment_id": donation.provider_payment_id,
        "amount": str(donation.amount),
        "currency": donation.currency,
        "card_id": donation.card_id,
        "status": outcome,
        "failed_reason": "" if outcome == "success" else "Dev checkout",
    }
    body, signature = adapter.sign_payload(payload)
    result = adapter.parse_result(payload, headers={"X-Dev-Signature": signature}, raw_body=body.encode("utf-8"))
    return apply_provider_result(result)

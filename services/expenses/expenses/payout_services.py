from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from ekomek_common.crypto import decrypt_value
from ekomek_common.outbox import enqueue_event

from .ledger_services import LedgerEntryType, record_ledger_entry
from .masking import contains_sensitive
from .payout_models import Invoice, InvoiceStatus, Payout, PayoutEvent, PayoutStatus, ProcessedPayoutCallback
from .payout_providers import get_payout_adapter
from .payout_providers.exceptions import PayoutMismatchError
from .payout_providers.types import ProviderPayoutResult
from .workflow import ExpenseActionError, escrow_available, fetch_card, publish_totals

OPEN_PAYOUT_STATUSES = {PayoutStatus.REQUESTED, PayoutStatus.PROCESSING}


def append_payout_event(payout, event_type, payload=None, *, actor=None):
    safe_payload = {} if contains_sensitive(payload) else (payload or {})
    return PayoutEvent.objects.create(
        payout=payout,
        event_type=event_type,
        payload=safe_payload,
        actor_id=getattr(actor, "id", None),
        actor_role=getattr(actor, "role", "") or "",
    )


def _next_idempotency_key(invoice):
    attempt = invoice.payouts.count() + 1
    return f"invoice:{invoice.id}:payout:{attempt}"


@transaction.atomic
def request_payout(invoice, *, amount=None, actor=None, idempotency_key=None):
    invoice = Invoice.objects.select_for_update().select_related("organization").get(pk=invoice.pk)
    if invoice.status not in {InvoiceStatus.VERIFIED, InvoiceStatus.PARTIALLY_PAID}:
        raise ExpenseActionError("Выплата возможна только по подтверждённому счёту.")
    if invoice.organization.verification_status != "verified":
        raise ExpenseActionError("Организация-получатель не подтверждена.")
    existing = invoice.payouts.filter(status__in=OPEN_PAYOUT_STATUSES).first()
    if existing:
        return existing
    payout_amount = Decimal(str(amount if amount is not None else invoice.remaining_amount))
    if payout_amount <= 0:
        raise ExpenseActionError("Нечего выплачивать по этому счёту.")
    if payout_amount > invoice.remaining_amount:
        raise ExpenseActionError("Сумма выплаты больше остатка по счёту.")
    card = fetch_card(invoice.card_id) or {"id": invoice.card_id, "collected_amount": 0}
    if payout_amount > escrow_available(card) + invoice.remaining_amount:
        raise ExpenseActionError("Сумма превышает доступный эскроу-баланс.")
    key = (idempotency_key or "").strip() or _next_idempotency_key(invoice)
    existing_key = Payout.objects.filter(idempotency_key=key).first()
    if existing_key:
        return existing_key
    payout = Payout.objects.create(
        card_id=invoice.card_id,
        invoice=invoice,
        organization=invoice.organization,
        amount=payout_amount,
        currency=invoice.currency,
        status=PayoutStatus.REQUESTED,
        idempotency_key=key,
        requested_by_id=getattr(actor, "id", None),
    )
    append_payout_event(payout, "requested", {"amount": str(payout.amount)}, actor=actor)
    enqueue_event(
        "payout.requested",
        "payout",
        payout.id,
        {"payout_id": payout.id, "invoice_id": invoice.id, "card_id": invoice.card_id, "amount": str(payout.amount)},
    )
    iban = decrypt_value(invoice.organization.iban_encrypted)
    adapter = get_payout_adapter()
    session = adapter.create_payout(payout, iban)
    payout.provider = session.provider
    payout.provider_payout_id = session.provider_payout_id
    payout.status = PayoutStatus.PROCESSING
    payout.save(update_fields=["provider", "provider_payout_id", "status", "updated_at"])
    append_payout_event(
        payout,
        "processing",
        {"provider": session.provider, "provider_payout_id": session.provider_payout_id},
        actor=actor,
    )
    return payout


def _match_result(payout, result: ProviderPayoutResult):
    if str(result.payout_id) != str(payout.id):
        raise PayoutMismatchError("payout_id не совпадает с выплатой.")
    if result.card_id != payout.card_id:
        raise PayoutMismatchError("card_id в уведомлении провайдера не совпадает.")
    if Decimal(str(result.amount)) != payout.amount:
        raise PayoutMismatchError("Сумма в уведомлении провайдера не совпадает.")
    if (result.currency or "").upper() != (payout.currency or "").upper():
        raise PayoutMismatchError("Валюта в уведомлении провайдера не совпадает.")
    if payout.provider_payout_id and result.provider_payout_id != payout.provider_payout_id:
        raise PayoutMismatchError("provider_payout_id не совпадает.")


@transaction.atomic
def apply_payout_result(result: ProviderPayoutResult):
    payout = Payout.objects.select_for_update().select_related("invoice", "organization").filter(
        pk=result.payout_id
    ).first()
    if payout is None:
        raise ExpenseActionError("Выплата не найдена.")
    _match_result(payout, result)
    event_key = result.event_key or f"{result.provider_payout_id}:{result.status}"
    try:
        ProcessedPayoutCallback.objects.create(event_key=event_key, payout=payout)
    except IntegrityError:
        return payout
    if result.status in {"succeeded", "paid", "success"}:
        return _mark_payout_succeeded(payout)
    payout.status = PayoutStatus.FAILED
    payout.failure_reason = result.failed_reason or "Выплата отклонена провайдером."
    payout.processed_at = timezone.now()
    payout.save(update_fields=["status", "failure_reason", "processed_at", "updated_at"])
    append_payout_event(payout, "failed", {"reason": payout.failure_reason})
    enqueue_event(
        "payout.failed",
        "payout",
        payout.id,
        {"payout_id": payout.id, "invoice_id": payout.invoice_id, "card_id": payout.card_id},
    )
    publish_totals(payout.card_id)
    return payout


def _mark_payout_succeeded(payout):
    if payout.status == PayoutStatus.SUCCEEDED:
        return payout
    invoice = Invoice.objects.select_for_update().get(pk=payout.invoice_id)
    payout.status = PayoutStatus.SUCCEEDED
    payout.processed_at = timezone.now()
    payout.save(update_fields=["status", "processed_at", "updated_at"])
    invoice.paid_amount = invoice.paid_amount + payout.amount
    invoice.status = InvoiceStatus.PAID if invoice.paid_amount >= invoice.amount else InvoiceStatus.PARTIALLY_PAID
    invoice.save(update_fields=["paid_amount", "status", "updated_at"])
    record_ledger_entry(
        card_id=payout.card_id,
        entry_type=LedgerEntryType.PAYOUT,
        amount=payout.amount,
        source_type="payout",
        source_id=payout.id,
        idempotency_key=f"payout:{payout.id}:succeeded",
        currency=payout.currency,
        metadata={"invoice_id": payout.invoice_id},
    )
    append_payout_event(payout, "succeeded", {"amount": str(payout.amount)})
    enqueue_event(
        "payout.succeeded",
        "payout",
        payout.id,
        {"payout_id": payout.id, "invoice_id": payout.invoice_id, "card_id": payout.card_id, "amount": str(payout.amount)},
    )
    publish_totals(payout.card_id)
    return payout

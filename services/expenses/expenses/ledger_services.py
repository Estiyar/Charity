from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum

from .masking import contains_sensitive
from .models import LedgerEntry, LedgerEntryType

CREDIT_TYPES = {LedgerEntryType.DONATION, LedgerEntryType.REDISTRIBUTION_IN}
DEBIT_TYPES = {
    LedgerEntryType.EXPENSE,
    LedgerEntryType.PAYOUT,
    LedgerEntryType.REDISTRIBUTION_OUT,
}


def record_ledger_entry(
    *,
    card_id,
    entry_type,
    amount,
    source_type,
    source_id,
    idempotency_key,
    currency="KZT",
    metadata=None,
):
    payload = metadata or {}
    if contains_sensitive(payload):
        payload = {}
    try:
        with transaction.atomic():
            return LedgerEntry.objects.create(
                card_id=card_id,
                entry_type=entry_type,
                amount=Decimal(str(amount)),
                currency=currency,
                source_type=source_type,
                source_id=str(source_id),
                idempotency_key=idempotency_key,
                metadata=payload,
            )
    except IntegrityError:
        return LedgerEntry.objects.get(idempotency_key=idempotency_key)


def _sum_types(card_id, types):
    total = LedgerEntry.objects.filter(card_id=card_id, entry_type__in=types).aggregate(s=Sum("amount"))["s"]
    return Decimal(str(total or 0))


def ledger_totals(card_id):
    collected = _sum_types(card_id, CREDIT_TYPES)
    expenses = _sum_types(card_id, {LedgerEntryType.EXPENSE})
    payouts = _sum_types(card_id, {LedgerEntryType.PAYOUT})
    corrections = _sum_types(card_id, {LedgerEntryType.CORRECTION})
    redistributed = _sum_types(card_id, {LedgerEntryType.REDISTRIBUTION_OUT})
    available = collected - expenses - payouts - redistributed + corrections
    return {
        "total_collected": collected,
        "total_confirmed_expenses": expenses,
        "total_direct_payouts": payouts,
        "available_balance": available,
        "corrections": corrections,
        "redistributed": redistributed,
    }


def record_donation_credit(payload):
    amount = payload.get("amount")
    card_id = payload.get("card_id")
    donation_id = payload.get("donation_id")
    if amount is None or not card_id or not donation_id:
        return None
    return record_ledger_entry(
        card_id=card_id,
        entry_type=LedgerEntryType.DONATION,
        amount=amount,
        source_type="donation",
        source_id=donation_id,
        idempotency_key=f"donation:{donation_id}:credit",
        currency=payload.get("currency") or "KZT",
    )


def record_redistribution(payload):
    if payload.get("choice") != "redirect":
        return None
    amount = payload.get("amount")
    source_id = payload.get("card_id")
    target_id = payload.get("target_card_id")
    decision_id = payload.get("decision_id")
    if amount is None or not source_id or not target_id or not decision_id:
        return None
    record_ledger_entry(
        card_id=source_id,
        entry_type=LedgerEntryType.REDISTRIBUTION_OUT,
        amount=amount,
        source_type="redistribution",
        source_id=decision_id,
        idempotency_key=f"redistribution:{decision_id}:out",
    )
    return record_ledger_entry(
        card_id=target_id,
        entry_type=LedgerEntryType.REDISTRIBUTION_IN,
        amount=amount,
        source_type="redistribution",
        source_id=decision_id,
        idempotency_key=f"redistribution:{decision_id}:in",
    )

from decimal import Decimal

from ekomek_common.constants import PUBLIC_CARD_STATUSES

from .invoice_repositories import InvoiceRepository
from .ledger_services import ledger_totals
from .masking import mask_sensitive_text
from .models import ExpenseCategory, ExpenseStatus
from .repositories import ExpenseRepository
from .workflow import fetch_card


def public_report(card_id):
    card = fetch_card(card_id) or {}
    ledger = ledger_totals(card_id)
    expense_totals = ExpenseRepository().totals(card_id)
    reserved_invoices = InvoiceRepository().reserved_total(card_id)
    collected = ledger["total_collected"]
    if collected == 0:
        collected = Decimal(str(card.get("collected_amount") or 0))
    confirmed = ledger["total_confirmed_expenses"]
    pending = Decimal(str(expense_totals["pending"] or 0)) + reserved_invoices
    payouts = ledger["total_direct_payouts"]
    target = Decimal(str(card.get("target_amount") or 0))
    remaining = target - collected
    if remaining < 0:
        remaining = Decimal("0")
    items = [public_expense_payload(item) for item in ExpenseRepository().for_card(card_id, public_only=True)]
    items.extend(public_payout_payload(item) for item in InvoiceRepository().public_paid(card_id))
    return {
        "card_id": card_id,
        "total_collected": collected,
        "total_confirmed_expenses": confirmed,
        "total_pending_expenses": pending,
        "available_balance": collected - confirmed - pending - payouts,
        "total_direct_payouts": payouts,
        "remaining_target": remaining,
        "expenses": items,
    }


def public_expense_payload(expense):
    receipt = None
    if expense.publish_receipt and expense.public_file:
        receipt = expense.public_file.url
    return {
        "id": expense.id,
        "category": expense.category,
        "date": expense.date,
        "amount": expense.amount,
        "status": expense.status,
        "public_receipt_url": receipt,
        "purpose": mask_sensitive_text(expense.purpose)
        if expense.status in {ExpenseStatus.APPROVED, ExpenseStatus.PAID}
        else None,
        "kind": "expense",
    }


def public_payout_payload(payout):
    invoice = payout.invoice
    receipt = None
    if invoice.publish_receipt and invoice.public_file:
        receipt = invoice.public_file.url
    return {
        "id": f"payout-{payout.id}",
        "category": ExpenseCategory.CLINIC if payout.organization.kind == "clinic" else ExpenseCategory.OTHER,
        "date": invoice.date,
        "amount": payout.amount,
        "status": "paid",
        "public_receipt_url": receipt,
        "purpose": mask_sensitive_text(invoice.purpose),
        "kind": "payout",
    }


def card_is_public(card):
    return bool(card) and card.get("status") in PUBLIC_CARD_STATUSES

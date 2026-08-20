from decimal import Decimal

from .invoice_repositories import InvoiceRepository
from .ledger_services import ledger_totals
from .repositories import ExpenseRepository


def card_escrow_totals(card_id):
    expenses = ExpenseRepository().totals(card_id)
    payouts = ledger_totals(card_id)["total_direct_payouts"]
    reserved = InvoiceRepository().reserved_total(card_id)
    return {
        "spent": Decimal(str(expenses["spent"] or 0)) + payouts,
        "pending": Decimal(str(expenses["pending"] or 0)) + reserved,
        "approved_count": expenses["approved_count"],
        "last_approved_at": expenses["last_approved_at"],
    }

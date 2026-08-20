from decimal import Decimal

from .ledger_services import ledger_totals
from .models import ReconciliationReport
from .repositories import ExpenseRepository
from .workflow import fetch_card


def _as_decimal(value):
    return Decimal(str(value or 0))


def reconcile_card(card_id):
    card = fetch_card(card_id) or {}
    ledger = ledger_totals(card_id)
    expenses = ExpenseRepository().totals(card_id)
    cached_collected = _as_decimal(card.get("collected_amount"))
    cached_spent = _as_decimal(card.get("escrow_spent") if card.get("escrow_spent") is not None else expenses["spent"])
    differences = {}
    if ledger["total_collected"] and cached_collected != ledger["total_collected"]:
        differences["collected_amount"] = {
            "cached": str(cached_collected),
            "ledger": str(ledger["total_collected"]),
        }
    if _as_decimal(expenses["spent"]) != ledger["total_confirmed_expenses"]:
        differences["confirmed_expenses"] = {
            "expenses": str(expenses["spent"]),
            "ledger": str(ledger["total_confirmed_expenses"]),
        }
    if cached_spent != ledger["total_confirmed_expenses"] + ledger["total_direct_payouts"]:
        differences["escrow_spent"] = {
            "cached": str(cached_spent),
            "ledger": str(ledger["total_confirmed_expenses"] + ledger["total_direct_payouts"]),
        }
    report = ReconciliationReport.objects.create(
        card_id=card_id,
        matched=not differences,
        differences=differences,
    )
    return report


def reconcile_known_cards(card_ids):
    return [reconcile_card(card_id) for card_id in card_ids]

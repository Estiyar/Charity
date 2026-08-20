from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ekomek_common.http import ServiceClientError, cards_client
from ekomek_common.outbox import enqueue_event
from ekomek_common.validators import validate_upload

from .ledger_services import LedgerEntryType, record_ledger_entry
from .models import Expense, ExpenseCategory, ExpenseDecisionEvent, ExpenseStatus
from .money_totals import card_escrow_totals
from .receipts import build_public_receipt
from .repositories import PENDING_STATUSES

TRANSITIONS = {
    ExpenseStatus.DRAFT: {ExpenseStatus.PENDING_REVIEW, ExpenseStatus.CANCELED},
    ExpenseStatus.SUBMITTED: {ExpenseStatus.PENDING_REVIEW, ExpenseStatus.CANCELED},
    ExpenseStatus.PENDING_REVIEW: {
        ExpenseStatus.APPROVED,
        ExpenseStatus.REJECTED,
        ExpenseStatus.REVISION_REQUIRED,
        ExpenseStatus.CANCELED,
    },
    ExpenseStatus.REVISION_REQUIRED: {ExpenseStatus.PENDING_REVIEW, ExpenseStatus.CANCELED},
    ExpenseStatus.APPROVED: {ExpenseStatus.PAID},
    ExpenseStatus.REJECTED: set(),
    ExpenseStatus.PAID: set(),
    ExpenseStatus.CANCELED: set(),
}


class ExpenseActionError(Exception):
    pass


def fetch_card(card_id):
    try:
        return cards_client().get(f"/internal/cards/{card_id}/")
    except ServiceClientError:
        return None


def record_decision(expense, action, *, actor=None, reason=""):
    return ExpenseDecisionEvent.objects.create(
        expense=expense,
        action=action,
        reason=reason or "",
        actor_id=getattr(actor, "id", None),
        actor_role=getattr(actor, "role", "") or "",
    )


def publish_totals(card_id):
    totals = card_escrow_totals(card_id)
    payload = _json_totals(totals)
    enqueue_event("expense.totals_changed", "expense", card_id, {"card_id": card_id, **payload})
    try:
        cards_client().post(f"/internal/cards/{card_id}/escrow/", json=payload)
    except ServiceClientError:
        pass
    return totals


def _json_totals(totals):
    payload = {}
    for key, value in totals.items():
        if hasattr(value, "quantize"):
            payload[key] = str(value)
        elif isinstance(value, datetime):
            payload[key] = value.isoformat()
        elif isinstance(value, date):
            payload[key] = value.isoformat()
        else:
            payload[key] = value
    return payload


def escrow_available(card):
    totals = card_escrow_totals(card["id"])
    return Decimal(str(card["collected_amount"])) - Decimal(str(totals["spent"])) - Decimal(str(totals["pending"]))


def _transition(expense, target):
    allowed = TRANSITIONS.get(expense.status, set())
    if target not in allowed:
        raise ExpenseActionError("Это действие недоступно для текущего статуса расхода.")
    expense.status = target


def _attach_receipt(expense, uploaded):
    if uploaded is None:
        return
    validate_upload(uploaded)
    expense.file_name = uploaded.name
    expense.original_file = uploaded
    uploaded.seek(0)
    file_bytes = uploaded.read()
    uploaded.seek(0)
    expense.public_file.save(
        "receipt.png",
        build_public_receipt(expense, file_bytes, uploaded.name),
        save=False,
    )


@transaction.atomic
def create_expense(card, validated, *, actor=None, uploaded=None, submit=False):
    expense = Expense(
        card_id=card["id"],
        card_name=card.get("full_name", ""),
        date=validated["date"],
        category=validated.get("category") or ExpenseCategory.OTHER,
        purpose=validated["purpose"],
        amount=validated["amount"],
        comment=validated.get("comment") or "",
        submitted_by_id=getattr(actor, "id", None),
        status=ExpenseStatus.DRAFT,
        publish_receipt=bool(validated.get("publish_receipt", True)),
    )
    _attach_receipt(expense, uploaded)
    expense.save()
    record_decision(expense, "created", actor=actor)
    enqueue_event("expense.created", "expense", expense.id, {"expense_id": expense.id, "card_id": expense.card_id})
    if submit:
        return submit_expense(expense, actor=actor)
    return expense


def _ensure_funds(expense, card):
    available = escrow_available(card)
    if expense.status in PENDING_STATUSES:
        available += expense.amount
    if expense.amount > available:
        raise ExpenseActionError(f"Сумма превышает доступный эскроу-баланс ({available}).")


@transaction.atomic
def submit_expense(expense, *, actor=None):
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    card = fetch_card(expense.card_id) or {"id": expense.card_id, "collected_amount": 0}
    _ensure_funds(expense, card)
    _transition(expense, ExpenseStatus.PENDING_REVIEW)
    expense.submitted_at = timezone.now()
    expense.submitted_by_id = getattr(actor, "id", None) or expense.submitted_by_id
    expense.save()
    record_decision(expense, "submitted", actor=actor)
    enqueue_event("expense.submitted", "expense", expense.id, {"expense_id": expense.id, "card_id": expense.card_id})
    publish_totals(expense.card_id)
    return expense


@transaction.atomic
def approve_expense(expense, comment="", *, actor=None, publish_receipt=None):
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    _transition(expense, ExpenseStatus.APPROVED)
    expense.reviewed_at = timezone.now()
    expense.reviewed_by_id = getattr(actor, "id", None)
    expense.decision_reason = comment
    if comment:
        expense.moderator_comment = comment
    if publish_receipt is not None:
        expense.publish_receipt = publish_receipt
    expense.save()
    record_ledger_entry(
        card_id=expense.card_id,
        entry_type=LedgerEntryType.EXPENSE,
        amount=expense.amount,
        source_type="expense",
        source_id=expense.id,
        idempotency_key=f"expense:{expense.id}:approved",
    )
    record_decision(expense, "approved", actor=actor, reason=comment)
    enqueue_event("expense.approved", "expense", expense.id, {"expense_id": expense.id, "card_id": expense.card_id})
    publish_totals(expense.card_id)
    return expense


@transaction.atomic
def reject_expense(expense, comment, *, actor=None):
    if not comment:
        raise ExpenseActionError("Комментарий обязателен при отклонении.")
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    _transition(expense, ExpenseStatus.REJECTED)
    expense.reviewed_at = timezone.now()
    expense.reviewed_by_id = getattr(actor, "id", None)
    expense.decision_reason = comment
    expense.moderator_comment = comment
    expense.save()
    record_decision(expense, "rejected", actor=actor, reason=comment)
    enqueue_event("expense.rejected", "expense", expense.id, {"expense_id": expense.id, "card_id": expense.card_id})
    publish_totals(expense.card_id)
    return expense


@transaction.atomic
def request_expense_revision(expense, comment, *, actor=None, internal_comment=""):
    if not comment:
        raise ExpenseActionError("Комментарий обязателен при запросе доработки.")
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    _transition(expense, ExpenseStatus.REVISION_REQUIRED)
    expense.reviewed_at = timezone.now()
    expense.reviewed_by_id = getattr(actor, "id", None)
    expense.decision_reason = comment
    expense.moderator_comment = comment
    expense.save()
    record_decision(expense, "revision_required", actor=actor, reason=comment)
    from .comment_services import record_expense_comments

    record_expense_comments(expense, revision_body=comment, internal_body=internal_comment, actor=actor)
    card = fetch_card(expense.card_id) or {}
    enqueue_event(
        "expense.revision_required",
        "expense",
        expense.id,
        {
            "expense_id": expense.id,
            "card_id": expense.card_id,
            "author_id": card.get("author_id") or expense.submitted_by_id,
            "revision_comment": comment,
        },
    )
    publish_totals(expense.card_id)
    return expense


def request_expense_clarification(expense, comment, *, actor=None, internal_comment=""):
    return request_expense_revision(expense, comment, actor=actor, internal_comment=internal_comment)


@transaction.atomic
def cancel_expense(expense, *, actor=None):
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    _transition(expense, ExpenseStatus.CANCELED)
    expense.save(update_fields=["status", "updated_at"])
    record_decision(expense, "canceled", actor=actor)
    publish_totals(expense.card_id)
    return expense


@transaction.atomic
def mark_expense_paid(expense, *, payout_id=None, actor=None):
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    _transition(expense, ExpenseStatus.PAID)
    if payout_id:
        expense.payout_id = payout_id
    expense.save()
    record_decision(expense, "paid", actor=actor)
    return expense

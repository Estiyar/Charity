from django.db import transaction

from .models import Expense, ExpenseStatus
from .workflow import ExpenseActionError, _attach_receipt, record_decision

EDITABLE_EXPENSE_STATUSES = {ExpenseStatus.DRAFT, ExpenseStatus.REVISION_REQUIRED}


@transaction.atomic
def update_expense(expense, validated, *, actor=None, uploaded=None):
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    if expense.status not in EDITABLE_EXPENSE_STATUSES:
        raise ExpenseActionError("Редактировать можно только черновик или расход на доработке.")
    for field in ("date", "purpose", "amount", "comment", "category", "publish_receipt"):
        if field in validated:
            setattr(expense, field, validated[field])
    _attach_receipt(expense, uploaded)
    expense.save()
    record_decision(expense, "updated", actor=actor)
    return expense

from .models import Expense, ExpenseStatus


class ExpenseActionError(Exception):
    pass


def _ensure_pending(expense):
    if expense.status != ExpenseStatus.PENDING:
        raise ExpenseActionError("Действие доступно только для расхода на проверке.")


def approve_expense(expense, comment=""):
    _ensure_pending(expense)
    expense.status = ExpenseStatus.APPROVED
    if comment:
        expense.moderator_comment = comment
    expense.save(update_fields=["status", "moderator_comment", "updated_at"])
    return expense


def reject_expense(expense, comment):
    if not comment:
        raise ExpenseActionError("Комментарий обязателен при отклонении.")
    _ensure_pending(expense)
    expense.status = ExpenseStatus.REJECTED
    expense.moderator_comment = comment
    expense.save(update_fields=["status", "moderator_comment", "updated_at"])
    return expense


def request_expense_clarification(expense, comment):
    if not comment:
        raise ExpenseActionError("Комментарий обязателен при запросе уточнения.")
    _ensure_pending(expense)
    expense.status = ExpenseStatus.REJECTED
    expense.moderator_comment = comment
    expense.save(update_fields=["status", "moderator_comment", "updated_at"])
    return expense

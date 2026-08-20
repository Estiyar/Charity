from django.db.models import Sum

from .models import Expense, ExpenseStatus

PENDING_STATUSES = {ExpenseStatus.SUBMITTED, ExpenseStatus.PENDING_REVIEW, ExpenseStatus.REVISION_REQUIRED}
CONFIRMED_STATUSES = {ExpenseStatus.APPROVED, ExpenseStatus.PAID}
PUBLIC_STATUSES = {ExpenseStatus.APPROVED, ExpenseStatus.PAID}
REVIEW_QUEUE_STATUSES = {ExpenseStatus.SUBMITTED, ExpenseStatus.PENDING_REVIEW}


class ExpenseRepository:
    def for_card(self, card_id, public_only=False):
        queryset = Expense.objects.filter(card_id=card_id).order_by("-date", "-created_at")
        if public_only:
            queryset = queryset.filter(status__in=PUBLIC_STATUSES)
        return queryset

    def pending(self):
        return Expense.objects.filter(status__in=REVIEW_QUEUE_STATUSES).order_by("-created_at")

    def confirmed_total(self, card_id):
        return Expense.objects.filter(card_id=card_id, status__in=CONFIRMED_STATUSES).aggregate(
            s=Sum("amount")
        )["s"] or 0

    def pending_total(self, card_id):
        return Expense.objects.filter(card_id=card_id, status__in=PENDING_STATUSES).aggregate(
            s=Sum("amount")
        )["s"] or 0

    def totals(self, card_id):
        approved = Expense.objects.filter(card_id=card_id, status__in=CONFIRMED_STATUSES)
        last_approved = approved.order_by("-updated_at").values_list("updated_at", flat=True).first()
        spent = self.confirmed_total(card_id)
        pending = self.pending_total(card_id)
        return {
            "spent": spent,
            "pending": pending,
            "approved_count": approved.count(),
            "last_approved_at": last_approved,
        }

    def list_admin(self):
        return Expense.objects.order_by("-created_at")

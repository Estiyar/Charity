from celery import shared_task

from .models import Expense
from .reconcile import reconcile_card


@shared_task(name="expenses.tasks.reconcile_ledgers")
def reconcile_ledgers():
    card_ids = Expense.objects.values_list("card_id", flat=True).distinct()
    for card_id in card_ids:
        reconcile_card(card_id)

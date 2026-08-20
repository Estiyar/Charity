from django.core.management.base import BaseCommand

from expenses.models import Expense, LedgerEntry
from expenses.reconcile import reconcile_card


class Command(BaseCommand):
    help = "Сверить агрегаты расходов и collected_amount с ledger."

    def handle(self, *args, **options):
        card_ids = set(Expense.objects.values_list("card_id", flat=True))
        card_ids.update(LedgerEntry.objects.values_list("card_id", flat=True))
        matched = 0
        for card_id in sorted(card_ids):
            report = reconcile_card(card_id)
            if report.matched:
                matched += 1
                continue
            self.stdout.write(f"card {card_id}: {report.differences}")
        self.stdout.write(f"matched {matched}/{len(card_ids)}")

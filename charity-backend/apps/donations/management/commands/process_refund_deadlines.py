from django.core.management.base import BaseCommand

from apps.donations.services import process_expired_refund_deadlines


class Command(BaseCommand):
    help = "Истечение срока решений доноров: keep по умолчанию и архивация сбора"

    def handle(self, *args, **options):
        expired_count, archived_count = process_expired_refund_deadlines()
        self.stdout.write(
            self.style.SUCCESS(
                f"Истекло решений: {expired_count}. Архивировано сборов: {archived_count}."
            )
        )

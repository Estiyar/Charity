from django.core.management.base import BaseCommand

from payments.redistribution import process_expired_redistribution_deadlines


class Command(BaseCommand):
    help = "Expire pending redistribution decisions and archive cards when allowed."

    def handle(self, *args, **options):
        expired_count, card_count = process_expired_redistribution_deadlines()
        self.stdout.write(f"Expired {expired_count} decisions across {card_count} cards.")

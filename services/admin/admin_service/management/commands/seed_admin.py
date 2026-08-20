from django.core.management.base import BaseCommand

from admin_service.models import City, Diagnosis, PlatformSettings

CITIES = ["Алматы", "Астана", "Шымкент", "Караганда", "Актобе", "Павлодар"]
DIAGNOSES = ["Онкология", "Сахарный диабет", "Порок сердца", "ДЦП", "Травма"]


class Command(BaseCommand):
    help = "Seed admin dictionaries"

    def handle(self, *args, **options):
        PlatformSettings.get_solo()
        for name in CITIES:
            City.objects.get_or_create(name=name)
        for name in DIAGNOSES:
            Diagnosis.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Admin dictionaries seeded"))

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.medregistry.models import Gender, MedicalDiagnosis, MedicalRecord


PEOPLE = [
    {
        "iin": "850315301234",
        "full_name": "Айгуль Смагулова",
        "birth_date": date(1985, 3, 15),
        "gender": Gender.FEMALE,
        "city": "Алматы",
        "clinic": "Городская поликлиника №5",
        "diagnoses": [("Онкология", "II", date(2024, 6, 10))],
    },
    {
        "iin": "920712401567",
        "full_name": "Данияр Касымов",
        "birth_date": date(1992, 7, 12),
        "gender": Gender.MALE,
        "city": "Астана",
        "clinic": "Республиканский госпиталь",
        "diagnoses": [("Сахарный диабет", "I", date(2023, 11, 5))],
    },
    {
        "iin": "780901300789",
        "full_name": "Гульнара Толеуова",
        "birth_date": date(1978, 9, 1),
        "gender": Gender.FEMALE,
        "city": "Шымкент",
        "clinic": "Областная больница",
        "diagnoses": [("Порок сердца", "III", date(2022, 4, 18))],
    },
    {
        "iin": "010203301122",
        "full_name": "Арман Жумабеков",
        "birth_date": date(2001, 2, 3),
        "gender": Gender.MALE,
        "city": "Караганда",
        "clinic": "Детская поликлиника №2",
        "diagnoses": [("ДЦП", "тяжёлая", date(2015, 8, 20))],
    },
    {
        "iin": "950512400888",
        "full_name": "Мадина Оспанова",
        "birth_date": date(1995, 5, 12),
        "gender": Gender.FEMALE,
        "city": "Актобе",
        "clinic": "Травматологический центр",
        "diagnoses": [("Травма", "острая", date(2025, 1, 14))],
    },
    {
        "iin": "960101300567",
        "full_name": "Ерлан Нурланов",
        "birth_date": date(1996, 1, 1),
        "gender": Gender.MALE,
        "city": "Алматы",
        "clinic": "Онкологический центр",
        "diagnoses": [("Онкология", "I", date(2025, 3, 2))],
    },
    {
        "iin": "880420301999",
        "full_name": "Асель Бекенова",
        "birth_date": date(1988, 4, 20),
        "gender": Gender.FEMALE,
        "city": "Астана",
        "clinic": "Семейная поликлиника №12",
        "diagnoses": [],
    },
    {
        "iin": "930615402345",
        "full_name": "Нурлан Сейтжанов",
        "birth_date": date(1993, 6, 15),
        "gender": Gender.MALE,
        "city": "Павлодар",
        "clinic": "Городская поликлиника №3",
        "diagnoses": [],
    },
    {
        "iin": "870308301456",
        "full_name": "Жанар Абдуллаева",
        "birth_date": date(1987, 3, 8),
        "gender": Gender.FEMALE,
        "city": "Алматы",
        "clinic": "Поликлиника №7",
        "diagnoses": [],
    },
    {
        "iin": "890711401678",
        "full_name": "Бауыржан Ибраев",
        "birth_date": date(1989, 7, 11),
        "gender": Gender.MALE,
        "city": "Астана",
        "clinic": "Медицинский центр Астана",
        "diagnoses": [],
    },
    {
        "iin": "990101300999",
        "full_name": "Ерболат Мукашев",
        "birth_date": date(1990, 1, 1),
        "gender": Gender.MALE,
        "city": "Алматы",
        "clinic": "Частная клиника МедЛайф",
        "diagnoses": [("Онкология", "II", date(2024, 9, 12))],
    },
    {
        "iin": "880101300888",
        "full_name": "Алмаз Токтаров",
        "birth_date": date(1988, 1, 1),
        "gender": Gender.MALE,
        "city": "Астана",
        "clinic": "Медцентр Астана",
        "diagnoses": [("Онкология", "I", date(2023, 5, 20))],
    },
]


class Command(BaseCommand):
    help = "Загрузка тестовых данных медреестра"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Очистить данные медреестра перед загрузкой",
        )

    @transaction.atomic(using="medregistry")
    def handle(self, *args, **options):
        if options["clear"]:
            MedicalDiagnosis.objects.using("medregistry").all().delete()
            MedicalRecord.objects.using("medregistry").all().delete()

        if MedicalRecord.objects.using("medregistry").exists():
            self.stdout.write(self.style.WARNING("Данные медреестра уже загружены. Используйте --clear."))
            return

        for person in PEOPLE:
            diagnoses = person.pop("diagnoses")
            record = MedicalRecord.objects.create(**person)
            for name, stage, diagnosed_date in diagnoses:
                MedicalDiagnosis.objects.create(
                    record=record,
                    name=name,
                    stage=stage,
                    diagnosed_date=diagnosed_date,
                )

        self.stdout.write(self.style.SUCCESS(f"Загружено записей: {len(PEOPLE)}"))

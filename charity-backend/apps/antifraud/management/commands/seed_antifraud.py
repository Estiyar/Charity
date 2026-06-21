from django.core.management.base import BaseCommand
from django.db import transaction

from apps.antifraud.models import FraudProfile, RiskLevel

PROFILES = [
    {
        "iin": "880420301999",
        "full_name": "Асель Бекенова",
        "risk_score": 5,
        "risk_level": RiskLevel.LOW,
        "reasons": ["Нет подозрительной активности"],
    },
    {
        "iin": "930615402345",
        "full_name": "Нурлан Сейтжанов",
        "risk_score": 8,
        "risk_level": RiskLevel.LOW,
        "reasons": ["Чистая кредитная история"],
    },
    {
        "iin": "850315301234",
        "full_name": "Айгуль Смагулова",
        "risk_score": 12,
        "risk_level": RiskLevel.LOW,
        "reasons": ["Проверенный получатель помощи"],
    },
    {
        "iin": "920712401567",
        "full_name": "Данияр Касымов",
        "risk_score": 18,
        "risk_level": RiskLevel.LOW,
        "reasons": ["Нет жалоб"],
    },
    {
        "iin": "780901300789",
        "full_name": "Гульнара Толеуова",
        "risk_score": 25,
        "risk_level": RiskLevel.LOW,
        "reasons": ["Стабильный профиль"],
    },
    {
        "iin": "010203301122",
        "full_name": "Арман Жумабеков",
        "risk_score": 35,
        "risk_level": RiskLevel.MEDIUM,
        "reasons": ["Несколько обращений за помощью"],
    },
    {
        "iin": "950512400888",
        "full_name": "Мадина Оспанова",
        "risk_score": 42,
        "risk_level": RiskLevel.MEDIUM,
        "reasons": ["Недавняя смена контактных данных"],
    },
    {
        "iin": "990101300999",
        "full_name": "Ерболат Мукашев",
        "risk_score": 92,
        "risk_level": RiskLevel.HIGH,
        "reasons": [
            "Множественные мошеннические заявки",
            "Поддельные медицинские документы",
        ],
    },
    {
        "iin": "880101300888",
        "full_name": "Алмаз Токтаров",
        "risk_score": 88,
        "risk_level": RiskLevel.HIGH,
        "reasons": [
            "Заблокирован в других благотворительных фондах",
            "Подозрение на сбор под чужим именем",
        ],
    },
]


class Command(BaseCommand):
    help = "Загрузка тестовых данных антифрода"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Очистить данные антифрода перед загрузкой",
        )

    @transaction.atomic(using="antifraud")
    def handle(self, *args, **options):
        if options["clear"]:
            FraudProfile.objects.using("antifraud").all().delete()

        if FraudProfile.objects.using("antifraud").exists():
            self.stdout.write(self.style.WARNING("Данные антифрода уже загружены. Используйте --clear."))
            return

        for profile in PROFILES:
            FraudProfile.objects.create(**profile)

        self.stdout.write(self.style.SUCCESS(f"Загружено профилей: {len(PROFILES)}"))

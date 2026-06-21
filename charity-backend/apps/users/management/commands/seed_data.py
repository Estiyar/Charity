from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.cards.models import City, Diagnosis, FundraisingCard
from apps.documents.models import Document, DocumentStatus
from apps.donations.models import Donation
from apps.expenses.models import Expense, ExpenseStatus
from apps.moderation.models import ModerationLog
from apps.users.models import PlatformSettings, Role

User = get_user_model()
PASSWORD = "demo123456"


class Command(BaseCommand):
    help = "Загрузка тестовых данных (ТЗ раздел 29)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Очистить существующие данные перед загрузкой",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self._clear_data()
        if User.objects.filter(email="admin@charity.test").exists():
            self.stdout.write(self.style.WARNING("Данные уже загружены. Используйте --clear."))
            return
        users = self._create_users()
        cities, diagnoses = self._create_references()
        cards = self._create_cards(users["authors"])
        self._create_documents(cards)
        self._create_donations(cards, users["donors"])
        self._create_expenses(cards)
        self._create_moderation_logs(cards, users["moderators"])
        PlatformSettings.get_solo()
        self.stdout.write(self.style.SUCCESS("Тестовые данные загружены."))
        self.stdout.write("Учётные записи: пароль для всех — demo123456")
        self.stdout.write("  admin@charity.test")
        self.stdout.write("  moderator1@charity.test / moderator2@charity.test")
        self.stdout.write("  author1@charity.test / author2@charity.test / author3@charity.test")
        self.stdout.write("  donor1@charity.test … donor4@charity.test")

    def _clear_data(self):
        ModerationLog.objects.all().delete()
        Expense.objects.all().delete()
        Donation.objects.all().delete()
        Document.objects.all().delete()
        FundraisingCard.objects.all().delete()
        Diagnosis.objects.all().delete()
        City.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _create_users(self):
        admin = User.objects.create_user(
            email="admin@charity.test",
            password=PASSWORD,
            full_name="Админ Тестов",
            role=Role.ADMIN,
            is_staff=True,
            iin="870308301456",
        )
        moderators = [
            User.objects.create_user(
                email=f"moderator{i}@charity.test",
                password=PASSWORD,
                full_name=f"Модератор {i}",
                role=Role.MODERATOR,
                iin=f"89071140167{i}",
            )
            for i in range(1, 3)
        ]
        authors = [
            User.objects.create_user(
                email=f"author{i}@charity.test",
                password=PASSWORD,
                full_name=f"Автор {i}",
                role=Role.AUTHOR,
                iin=f"85031530123{i}",
            )
            for i in range(1, 4)
        ]
        donors = [
            User.objects.create_user(
                email=f"donor{i}@charity.test",
                password=PASSWORD,
                full_name=f"Донор {i}",
                role=Role.DONOR,
                iin=f"93061540234{i}",
            )
            for i in range(1, 5)
        ]
        return {"admin": admin, "moderators": moderators, "authors": authors, "donors": donors}

    def _create_references(self):
        city_names = ["Алматы", "Астана", "Шымкент", "Караганда", "Актобе"]
        diagnosis_names = [
            "Онкология",
            "ДЦП",
            "Сахарный диабет",
            "Порок сердца",
            "Травма",
        ]
        cities = [City.objects.create(name=name) for name in city_names]
        diagnoses = [Diagnosis.objects.create(name=name) for name in diagnosis_names]
        return cities, diagnoses

    def _create_cards(self, authors):
        base = date.today() + timedelta(days=60)
        specs = [
            ("draft", authors[0], "500000", "0", "Черновик сбора"),
            ("pending_moderation", authors[0], "400000", "0", "На модерации"),
            ("revision_required", authors[1], "350000", "0", "На доработке"),
            ("rejected", authors[1], "300000", "0", "Отклонённый сбор"),
            ("active", authors[0], "600000", "120000", "Активный сбор 1"),
            ("active", authors[1], "450000", "80000", "Активный сбор 2"),
            ("completed", authors[2], "200000", "200000", "Завершён с остатком"),
            ("deceased", authors[2], "250000", "180000", "Получатель умер"),
            ("redistribution", authors[0], "300000", "150000", "Перераспределение"),
            ("active", authors[2], "500000", "50000", "Целевой для transfer"),
        ]
        cards = []
        for index, (status, author, target, collected, name) in enumerate(specs):
            card = FundraisingCard.objects.create(
                author=author,
                full_name=name,
                diagnosis="Онкология" if index % 2 == 0 else "ДЦП",
                city="Алматы" if index % 2 == 0 else "Астана",
                clinic="Городская поликлиника",
                age=25 + index,
                target_amount=Decimal(target),
                collected_amount=Decimal(collected),
                end_date=base + timedelta(days=index * 5),
                status=status,
                iin_encrypted=f"99010130012{index}",
                recipient_iin=f"99010130012{index}",
                document_number_encrypted=f"1234567{index}",
                contact_phone="+7 777 123 45 67",
                contact_email=f"card{index}@example.com",
            )
            cards.append(card)
        return cards

    def _create_documents(self, cards):
        count = 0
        for card in cards:
            for doc_index in range(2):
                Document.objects.create(
                    card=card,
                    file_name=f"doc_{card.id}_{doc_index}.pdf",
                    file_type="pdf",
                    file_url=SimpleUploadedFile(
                        f"seed_{card.id}_{doc_index}.pdf",
                        b"%PDF-1.4 seed",
                        content_type="application/pdf",
                    ),
                    status=DocumentStatus.VERIFIED if doc_index == 0 else DocumentStatus.UPLOADED,
                )
                count += 1
        assert count == 20

    def _create_donations(self, cards, donors):
        active_cards = [card for card in cards if card.status in {"active", "completed", "deceased", "redistribution"}]
        count = 0
        for index in range(30):
            card = active_cards[index % len(active_cards)]
            donor = donors[index % len(donors)]
            Donation.objects.create(
                card=card,
                donor=donor,
                donor_name=donor.full_name,
                amount=Decimal("1000") + Decimal(index * 500),
                payment_method="card" if index % 2 == 0 else "transfer",
            )
            count += 1
        assert count == 30

    def _create_expenses(self, cards):
        statuses = [
            ExpenseStatus.PENDING,
            ExpenseStatus.APPROVED,
            ExpenseStatus.REJECTED,
            ExpenseStatus.PENDING,
            ExpenseStatus.APPROVED,
            ExpenseStatus.PENDING,
            ExpenseStatus.APPROVED,
            ExpenseStatus.PENDING,
            ExpenseStatus.APPROVED,
            ExpenseStatus.PENDING,
        ]
        spendable = [card for card in cards if card.status in {"active", "completed", "deceased", "redistribution"}]
        for index, expense_status in enumerate(statuses):
            card = spendable[index % len(spendable)]
            Expense.objects.create(
                card=card,
                date=date.today() - timedelta(days=index + 1),
                purpose=f"Расход {index + 1}",
                amount=Decimal("5000") + Decimal(index * 1000),
                comment="Тестовый расход",
                status=expense_status,
                moderator_comment="Отклонено" if expense_status == ExpenseStatus.REJECTED else "",
            )

    def _create_moderation_logs(self, cards, moderators):
        for card in cards[:5]:
            ModerationLog.objects.create(
                card=card,
                moderator=moderators[0],
                action="review",
                comment="Проверка тестовых данных",
            )

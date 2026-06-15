from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus
from apps.expenses.models import Expense, ExpenseStatus

User = get_user_model()


class ExpenseAPITestCase(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор Тест",
            role="author",
        )
        self.other_author = User.objects.create_user(
            email="other@example.com",
            password="securepass123",
            full_name="Другой Автор",
            role="author",
        )
        self.moderator = User.objects.create_user(
            email="mod@example.com",
            password="securepass123",
            full_name="Модератор",
            role="moderator",
        )
        self.active_card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Айгуль Смагулова",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("500000.00"),
            collected_amount=Decimal("100000.00"),
            end_date=date.today() + timedelta(days=90),
            status=CardStatus.ACTIVE,
        )
        self.draft_card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Черновик",
            diagnosis="Тест",
            city="Астана",
            target_amount=Decimal("100000.00"),
            end_date=date.today() + timedelta(days=30),
            status=CardStatus.DRAFT,
        )

    def _expense_payload(self, **overrides):
        data = {
            "date": str(date.today()),
            "purpose": "Лекарства",
            "amount": "15000.00",
            "comment": "Чек из аптеки",
        }
        data.update(overrides)
        return data

    def _create_expense(self, card=None, **overrides):
        card = card or self.active_card
        expense = Expense.objects.create(
            card=card,
            date=date.today(),
            purpose=overrides.get("purpose", "Лекарства"),
            amount=Decimal(overrides.get("amount", "15000.00")),
            comment=overrides.get("comment", ""),
            status=overrides.get("status", ExpenseStatus.PENDING),
        )
        return expense

    def test_author_creates_expense(self):
        pdf = SimpleUploadedFile(
            "receipt.pdf",
            b"%PDF-1.4 test",
            content_type="application/pdf",
        )
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.active_card.id}/expenses/",
            {**self._expense_payload(), "file": pdf},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], ExpenseStatus.PENDING)
        self.assertEqual(response.data["purpose"], "Лекарства")
        self.assertEqual(self.active_card.expenses.count(), 1)

    def test_create_expense_exceeds_escrow_rejected(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.active_card.id}/expenses/",
            self._expense_payload(amount="150000.00"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data)

    def test_create_expense_for_draft_card_rejected(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.draft_card.id}/expenses/",
            self._expense_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_foreign_author_cannot_create_expense(self):
        self.client.force_authenticate(user=self.other_author)
        response = self.client.post(
            f"/api/cards/{self.active_card.id}/expenses/",
            self._expense_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_list_shows_only_approved_expenses(self):
        approved = self._create_expense(status=ExpenseStatus.APPROVED, purpose="Одобрено")
        self._create_expense(status=ExpenseStatus.PENDING, purpose="На проверке")
        self._create_expense(status=ExpenseStatus.REJECTED, purpose="Отклонено")

        response = self.client.get(f"/api/cards/{self.active_card.id}/expenses/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], approved.id)
        self.assertEqual(response.data[0]["status"], ExpenseStatus.APPROVED)

    def test_author_sees_all_expenses(self):
        self._create_expense(status=ExpenseStatus.PENDING)
        self._create_expense(status=ExpenseStatus.APPROVED, amount="5000.00")
        self.client.force_authenticate(user=self.author)
        response = self.client.get(f"/api/cards/{self.active_card.id}/expenses/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_moderator_approves_expense(self):
        expense = self._create_expense()
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/expenses/{expense.id}/approve/",
            {"comment": "Подтверждено"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ExpenseStatus.APPROVED)
        expense.refresh_from_db()
        self.assertEqual(expense.status, ExpenseStatus.APPROVED)

    def test_moderator_rejects_expense_requires_comment(self):
        expense = self._create_expense()
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/expenses/{expense.id}/reject/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        expense.refresh_from_db()
        self.assertEqual(expense.status, ExpenseStatus.PENDING)

    def test_moderator_rejects_expense_with_comment(self):
        expense = self._create_expense()
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/expenses/{expense.id}/reject/",
            {"comment": "Недостаточно документов"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ExpenseStatus.REJECTED)
        self.assertEqual(response.data["moderator_comment"], "Недостаточно документов")

    def test_moderator_requests_clarification(self):
        expense = self._create_expense()
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/expenses/{expense.id}/request-clarification/",
            {"comment": "Приложите оригинал чека"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], ExpenseStatus.REJECTED)
        self.assertEqual(response.data["moderator_comment"], "Приложите оригинал чека")

    def test_non_moderator_cannot_approve_expense(self):
        expense = self._create_expense()
        self.client.force_authenticate(user=self.author)
        response = self.client.post(f"/api/expenses/{expense.id}/approve/", format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderation_expense_list_pending_only(self):
        pending = self._create_expense()
        self._create_expense(status=ExpenseStatus.APPROVED, amount="3000.00")
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get("/api/moderation/expenses/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], pending.id)

    def test_escrow_updates_after_approval(self):
        self._create_expense(amount="20000.00", status=ExpenseStatus.APPROVED)
        pending = self._create_expense(amount="10000.00", status=ExpenseStatus.PENDING)

        self.assertEqual(self.active_card.escrow_spent, Decimal("20000.00"))
        self.assertEqual(self.active_card.escrow_pending, Decimal("10000.00"))
        self.assertEqual(self.active_card.escrow_available, Decimal("70000.00"))
        self.assertEqual(self.active_card.escrow_balance, Decimal("80000.00"))

        self.client.force_authenticate(user=self.moderator)
        self.client.post(f"/api/expenses/{pending.id}/approve/", format="json")
        self.active_card.refresh_from_db()

        self.assertEqual(self.active_card.escrow_spent, Decimal("30000.00"))
        self.assertEqual(self.active_card.escrow_pending, Decimal("0"))
        self.assertEqual(self.active_card.escrow_available, Decimal("70000.00"))

    def test_upload_invalid_extension_rejected(self):
        doc = SimpleUploadedFile(
            "virus.exe",
            b"bad",
            content_type="application/octet-stream",
        )
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.active_card.id}/expenses/",
            {**self._expense_payload(), "file": doc},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_oversized_file_rejected(self):
        large = SimpleUploadedFile(
            "big.pdf",
            BytesIO(b"x" * (11 * 1024 * 1024)).read(),
            content_type="application/pdf",
        )
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.active_card.id}/expenses/",
            {**self._expense_payload(), "file": large},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

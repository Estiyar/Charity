from django.utils import timezone
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import CardStatus, RelationshipType, Role, VIEWABLE_PUBLIC_STATUSES
from ekomek_common.outbox_app.models import OutboxEvent
from ekomek_common.reports import ReportCategory

from .models import FundraisingCard


class CardReportsSuspensionTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        self.reporter = make_principal(21, Role.DONOR, email="reporter@test.com")
        self.moderator = make_principal(31, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.card = FundraisingCard.objects.create(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="Test Fundraiser",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("10000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.ACTIVE,
            is_self=True,
            relationship_type=RelationshipType.SELF,
            moderation_verified_at=timezone.now(),
        )
        moderation = patch("cards.report_views.moderation_client")
        self.moderation_client = moderation.start()
        self.addCleanup(moderation.stop)
        self.moderation_client.return_value.post.return_value = {
            "id": 1,
            "card_id": self.card.id,
            "category": ReportCategory.SUSPECTED_FRAUD,
            "status": "pending",
        }

    def test_suspended_card_is_publicly_viewable(self):
        self.card.status = CardStatus.SUSPENDED
        self.card.suspend_reason = "Проверка"
        self.card.save(update_fields=["status", "suspend_reason", "updated_at"])
        response = self.client.get(f"/api/cards/{self.card.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], CardStatus.SUSPENDED)
        self.assertFalse(response.data["can_donate"])

    def test_create_report_proxies_to_moderation(self):
        response = self.client.post(
            f"/api/cards/{self.card.id}/reports/",
            {
                "category": ReportCategory.INCORRECT_INFORMATION,
                "description": "Неверно указан диагноз в описании сбора",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.moderation_client.return_value.post.assert_called_once()

    def test_suspend_requires_reason_and_permission(self):
        self.client.force_authenticate(self.author)
        denied = self.client.post(f"/api/cards/{self.card.id}/suspend/", {"reason": "test"}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.moderator)
        missing = self.client.post(f"/api/cards/{self.card.id}/suspend/", {}, format="json")
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

        ok = self.client.post(
            f"/api/cards/{self.card.id}/suspend/",
            {"reason": "Подозрение на мошенничество"},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK, ok.data)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.SUSPENDED)
        self.assertEqual(self.card.status_before_suspend, CardStatus.ACTIVE)
        self.assertTrue(
            OutboxEvent.objects.filter(event_type="card.suspended", aggregate_id=str(self.card.id)).exists()
        )

    def test_unsuspend_restores_previous_status(self):
        self.card.status = CardStatus.SUSPENDED
        self.card.status_before_suspend = CardStatus.ACTIVE
        self.card.suspend_reason = "Проверка"
        self.card.save(
            update_fields=["status", "status_before_suspend", "suspend_reason", "updated_at"]
        )
        self.client.force_authenticate(self.moderator)
        response = self.client.post(
            f"/api/cards/{self.card.id}/unsuspend/",
            {"reason": "Проверка завершена, нарушений нет"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.ACTIVE)
        self.assertEqual(self.card.suspend_reason, "")

    def test_internal_report_risk_updates_card(self):
        response = self.client.post(
            f"/internal/cards/{self.card.id}/report-risk/",
            {"report_risk_score": 35, "unique_report_count": 2},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.report_risk_score, 35)
        self.assertEqual(self.card.unique_report_count, 2)

    def test_internal_auto_suspend(self):
        response = self.client.post(
            f"/internal/cards/{self.card.id}/suspend/",
            {"reason": "Auto", "source": "report"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.SUSPENDED)

    def test_viewable_statuses_include_suspended(self):
        self.assertIn(CardStatus.SUSPENDED, VIEWABLE_PUBLIC_STATUSES)

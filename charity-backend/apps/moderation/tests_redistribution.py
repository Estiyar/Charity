from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus
from apps.moderation.models import RedistributionDecision

User = get_user_model()


class RedistributionAPITestCase(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор",
            role="author",
        )
        self.moderator = User.objects.create_user(
            email="mod@example.com",
            password="securepass123",
            full_name="Модератор",
            role="moderator",
        )
        self.target_card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Целевой сбор",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("500000.00"),
            collected_amount=Decimal("10000.00"),
            end_date=date.today() + timedelta(days=90),
            status=CardStatus.ACTIVE,
        )
        self.completed_card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Завершённый сбор",
            diagnosis="ДЦП",
            city="Астана",
            target_amount=Decimal("200000.00"),
            collected_amount=Decimal("200000.00"),
            end_date=date.today() + timedelta(days=30),
            status=CardStatus.COMPLETED,
        )

    def test_public_can_read_redistribution_history(self):
        RedistributionDecision.objects.create(
            card=self.completed_card,
            decision_type=RedistributionDecision.DecisionType.REFUND,
            comment="Демо-возврат",
            created_by=self.moderator,
        )
        response = self.client.get(
            f"/api/cards/{self.completed_card.id}/redistribution/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["decisions"]), 1)

    def test_moderator_creates_refund_decision(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/cards/{self.completed_card.id}/redistribution/",
            {"decision_type": "refund", "comment": "Вернуть донорам"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.completed_card.refresh_from_db()
        self.assertEqual(self.completed_card.status, CardStatus.REDISTRIBUTION)

    def test_transfer_requires_target_card(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/cards/{self.completed_card.id}/redistribution/",
            {"decision_type": "transfer"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_to_active_card(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/cards/{self.completed_card.id}/redistribution/",
            {
                "decision_type": "transfer",
                "target_card_id": self.target_card.id,
                "comment": "Перевод на другой сбор",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["target_card"], self.target_card.id)

    def test_hold_keeps_status(self):
        self.completed_card.status = CardStatus.ACTIVE
        self.completed_card.save()
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/cards/{self.completed_card.id}/redistribution/",
            {"decision_type": "hold", "comment": "Ожидание проверки"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.completed_card.refresh_from_db()
        self.assertEqual(self.completed_card.status, CardStatus.ACTIVE)

    def test_moderation_redistribution_card_list(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get("/api/moderation/redistribution/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item["id"] == self.completed_card.id for item in response.data))

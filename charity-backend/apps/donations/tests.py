from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus
from apps.donations.models import Donation
from apps.donations.serializers import DONATION_SUCCESS_MESSAGE

User = get_user_model()


class DonationAPITestCase(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор",
            role="author",
        )
        self.active_card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Айгуль Смагулова",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("500000.00"),
            collected_amount=Decimal("10000.00"),
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
        self.donate_payload = {
            "amount": "5000.00",
            "donor_name": "Иван Донор",
            "contact": "+7 777 111 22 33",
            "payment_method": "card",
            "personal_data_consent": True,
        }

    def test_donate_increases_collected_amount(self):
        response = self.client.post(
            f"/api/cards/{self.active_card.id}/donate/",
            self.donate_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], DONATION_SUCCESS_MESSAGE)
        self.assertEqual(response.data["collected_amount"], "15000.00")

        self.active_card.refresh_from_db()
        self.assertEqual(self.active_card.collected_amount, Decimal("15000.00"))
        self.assertEqual(Donation.objects.filter(card=self.active_card).count(), 1)

    def test_donate_requires_consent(self):
        payload = {**self.donate_payload, "personal_data_consent": False}
        response = self.client.post(
            f"/api/cards/{self.active_card.id}/donate/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_donate_non_active_card_rejected(self):
        response = self.client.post(
            f"/api/cards/{self.draft_card.id}/donate/",
            self.donate_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("активных", response.data["detail"])

    def test_donate_completed_card_rejected(self):
        self.active_card.status = CardStatus.COMPLETED
        self.active_card.save(update_fields=["status"])

        response = self.client.post(
            f"/api/cards/{self.active_card.id}/donate/",
            self.donate_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_donations_for_public_card(self):
        Donation.objects.create(
            card=self.active_card,
            donor_name="Тест",
            amount=Decimal("1000.00"),
            payment_method="card",
        )
        response = self.client.get(f"/api/cards/{self.active_card.id}/donations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_donations_hidden_for_draft(self):
        response = self.client.get(f"/api/cards/{self.draft_card.id}/donations/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_my_donations_requires_auth(self):
        response = self.client.get("/api/donations/my/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_donations_returns_only_current_user_donations(self):
        donor = User.objects.create_user(
            email="donor@example.com",
            password="securepass123",
            full_name="Иван Донор",
            role="donor",
        )
        other_donor = User.objects.create_user(
            email="other@example.com",
            password="securepass123",
            full_name="Другой донор",
            role="donor",
        )
        Donation.objects.create(
            card=self.active_card,
            donor=donor,
            donor_name=donor.full_name,
            amount=Decimal("5000.00"),
            payment_method="card",
        )
        Donation.objects.create(
            card=self.active_card,
            donor=other_donor,
            donor_name=other_donor.full_name,
            amount=Decimal("3000.00"),
            payment_method="card",
        )
        self.client.force_authenticate(user=donor)
        response = self.client.get("/api/donations/my/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amount"], "5000.00")
        self.assertEqual(response.data[0]["card_name"], self.active_card.full_name)


class PlatformStatsAPITestCase(APITestCase):
    def test_stats_endpoint(self):
        author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор",
            role="author",
        )
        FundraisingCard.objects.create(
            author=author,
            full_name="Активный сбор",
            diagnosis="Тест",
            city="Алматы",
            target_amount=Decimal("100000.00"),
            collected_amount=Decimal("5000.00"),
            end_date=date.today() + timedelta(days=30),
            status=CardStatus.ACTIVE,
        )
        response = self.client.get("/api/stats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["active_fundraisers"], 1)
        self.assertIn("total_collected", response.data)
        self.assertIn("donors_count", response.data)
        self.assertIn("verified_documents", response.data)

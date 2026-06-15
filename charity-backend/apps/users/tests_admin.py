from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cards.models import City, Diagnosis, FundraisingCard
from apps.common.card_status import CardStatus
from apps.moderation.models import ModerationLog
from apps.users.models import PlatformSettings, Role, UserStatus

User = get_user_model()


class AdminAPITestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="securepass123",
            full_name="Админ",
            role=Role.ADMIN,
        )
        self.moderator = User.objects.create_user(
            email="mod@example.com",
            password="securepass123",
            full_name="Модератор",
            role=Role.MODERATOR,
        )
        self.donor = User.objects.create_user(
            email="donor@example.com",
            password="securepass123",
            full_name="Донор",
            role=Role.DONOR,
        )
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор",
            role=Role.AUTHOR,
        )
        self.card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Тестовая карточка",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("100000.00"),
            end_date=date.today() + timedelta(days=30),
            status=CardStatus.DRAFT,
        )

    def test_admin_lists_users(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 4)

    def test_non_admin_forbidden(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get("/api/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_assigns_role(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/admin/users/{self.donor.id}/",
            {"role": Role.AUTHOR},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.role, Role.AUTHOR)

    def test_admin_blocks_user(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/admin/users/{self.donor.id}/",
            {"status": UserStatus.BLOCKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.status, UserStatus.BLOCKED)

    def test_admin_changes_card_status(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/admin/cards/{self.card.id}/",
            {"status": CardStatus.PENDING_MODERATION},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.PENDING_MODERATION)

    def test_admin_set_status_bypasses_transitions(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/admin/cards/{self.card.id}/set-status/",
            {"status": CardStatus.ACTIVE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.ACTIVE)
        self.assertEqual(
            ModerationLog.objects.filter(card=self.card, action="admin_set_status").count(),
            1,
        )

    def test_admin_manages_references(self):
        self.client.force_authenticate(user=self.admin)
        city_response = self.client.post(
            "/api/admin/cities/",
            {"name": "Павлодар"},
            format="json",
        )
        self.assertEqual(city_response.status_code, status.HTTP_201_CREATED)
        diagnosis_response = self.client.post(
            "/api/admin/diagnoses/",
            {"name": "Астма"},
            format="json",
        )
        self.assertEqual(diagnosis_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(City.objects.filter(name="Павлодар").count(), 1)
        self.assertEqual(Diagnosis.objects.filter(name="Астма").count(), 1)

    def test_admin_settings(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/settings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["bank_integration_stub"])
        patch_response = self.client.patch(
            "/api/admin/settings/",
            {"site_name": "Charity Demo"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        settings = PlatformSettings.get_solo()
        self.assertEqual(settings.site_name, "Charity Demo")

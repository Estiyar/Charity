from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role, UserStatus

from .models import Profile
from .privacy import DEFAULT_PUBLIC_FIELDS


def identity_payload(user, **overrides):
    payload = {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": "+7 700 000 00 00",
        "iin_masked": "************",
        "birth_date": "1990-01-15",
        "role": user.role,
        "status": UserStatus.ECP_VERIFIED,
        "ecp_verification_id": 4,
        "ecp_locked_fields": ["full_name", "iin", "birth_date"],
        "last_login": "2026-08-17T10:00:00+00:00",
        "created_at": "2026-01-01T10:00:00+00:00",
    }
    payload.update(overrides)
    return payload


class ProfileAPITestCase(APITestCase):
    def setUp(self):
        self.donor = make_principal(5, Role.DONOR, email="donor@test.com", full_name="Донор Иванов")
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com", full_name="Автор Сборов")
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.admin = make_principal(33, Role.ADMIN, email="admin@test.com", full_name="Админ")

    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)

    @patch("profile.services.identity_client")
    def test_all_roles_can_open_own_profile(self, mock_client):
        for user in (self.donor, self.author, self.moderator, self.admin):
            mock_client.return_value.get.return_value = identity_payload(user)
            self.client.force_authenticate(user)
            response = self.client.get("/api/profile/me")
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data["email"], user.email)
            self.assertEqual(response.data["role"], user.role)
            self.assertIn("public_fields", response.data)

    @patch("profile.services.identity_client")
    def test_owner_can_edit_allowed_fields_and_privacy(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.donor)
        self.client.force_authenticate(self.donor)
        self.client.get("/api/profile/me")
        response = self.client.patch(
            "/api/profile/me",
            {
                "bio": "Помогаю открыто",
                "city": "Алматы",
                "phone": "+7 777 111 22 33",
                "public_fields": ["full_name", "avatar", "role", "city", "bio"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["bio"], "Помогаю открыто")
        self.assertEqual(response.data["city"], "Алматы")
        self.assertEqual(response.data["phone"], "+7 777 111 22 33")
        self.assertIn("city", response.data["public_fields"])
        self.assertNotIn("880420301999", str(response.data))

    @patch("profile.services.identity_client")
    def test_owner_cannot_change_ecp_locked_name(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.author)
        self.client.force_authenticate(self.author)
        self.client.get("/api/profile/me")
        response = self.client.patch("/api/profile/me", {"full_name": "Другое Имя"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", response.data)

    @patch("profile.services.identity_client")
    def test_public_profile_hides_private_fields(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.donor)
        self.client.force_authenticate(self.donor)
        self.client.patch(
            "/api/profile/me",
            {"bio": "Секрет", "city": "Астана", "public_fields": ["full_name", "role"]},
            format="json",
        )
        self.client.force_authenticate(None)
        response = self.client.get(f"/api/profile/{self.donor.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Донор Иванов")
        self.assertIsNone(response.data["bio"])
        self.assertIsNone(response.data["city"])
        self.assertIsNone(response.data["email"])
        self.assertIsNone(response.data["phone"])
        self.assertNotIn("iin_masked", response.data)
        self.assertNotIn("phone_masked", response.data)

    @patch("profile.services.identity_client")
    def test_moderator_sees_expanded_private_view(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.donor)
        self.client.force_authenticate(self.donor)
        self.client.patch("/api/profile/me", {"city": "Шымкент", "phone": "+7 701 222 33 44"}, format="json")
        self.client.force_authenticate(self.moderator)
        response = self.client.get(f"/api/profile/{self.donor.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["view"], "staff")
        self.assertEqual(response.data["city"], "Шымкент")
        self.assertEqual(response.data["phone"], "+7 701 222 33 44")
        self.assertEqual(response.data["iin_masked"], "************")
        self.assertEqual(response.data["ecp_status"], "verified")

    @patch("profile.services.identity_client")
    def test_admin_can_change_locked_full_name(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.author)
        self.client.force_authenticate(self.author)
        self.client.get("/api/profile/me")
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/profile/{self.author.id}",
            {"full_name": "ИВАНОВ ИВАН", "birth_date": "1988-04-20"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["full_name"], "ИВАНОВ ИВАН")
        self.assertEqual(response.data["birth_date"], "1988-04-20")
        self.assertEqual(response.data["age"], 38)

    @patch("profile.services.identity_client")
    def test_moderator_cannot_change_locked_fields(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.author)
        self.client.force_authenticate(self.author)
        self.client.get("/api/profile/me")
        self.client.force_authenticate(self.moderator)
        response = self.client.patch(
            f"/api/profile/{self.author.id}",
            {"full_name": "Чужое Имя"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("profile.services.identity_client")
    def test_owner_update_writes_audit_event(self, mock_client):
        from ekomek_common.outbox_app.models import OutboxEvent

        mock_client.return_value.get.return_value = identity_payload(self.donor)
        self.client.force_authenticate(self.donor)
        response = self.client.patch("/api/profile/me", {"city": "Караганда"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = OutboxEvent.objects.filter(event_type="profile.updated", aggregate_id=str(self.donor.id)).last()
        self.assertIsNotNone(event)
        self.assertIn("city", event.payload["fields"])

    @patch("profile.services.identity_client")
    def test_invalid_phone_rejected(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.donor)
        self.client.force_authenticate(self.donor)
        response = self.client.patch("/api/profile/me", {"phone": "123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("profile.services.identity_client")
    def test_missing_public_profile_is_not_found(self, mock_client):
        response = self.client.get("/api/profile/999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("profile.services.identity_client")
    def test_default_public_fields_are_safe(self, mock_client):
        mock_client.return_value.get.return_value = identity_payload(self.donor)
        self.client.force_authenticate(self.donor)
        me = self.client.get("/api/profile/me")
        self.assertEqual(me.data["public_fields"], DEFAULT_PUBLIC_FIELDS)
        profile = Profile.objects.get(user_id=self.donor.id)
        self.assertFalse(profile.is_public_phone)
        self.assertFalse(profile.is_public_email)

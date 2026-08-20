from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from ekomek_common.constants import Role, UserStatus
from ekomek_common.crypto import hmac_hash
from ekomek_common.http import ServiceClientError
from ekomek_common.logging import redact_sensitive
from ekomek_common.masking import mask_iin
from ekomek_common.outbox_app.models import OutboxEvent

from .models import User

RAW_IIN = "880420301999"
LOGIN_IIN = "930615402345"


class RegisterAPITestCase(APITestCase):
    url = "/api/auth/register"

    def setUp(self):
        patcher = patch("identity.ecp_services.verification_client")
        mock_client = patcher.start()
        self.addCleanup(patcher.stop)
        mock_client.return_value.post.side_effect = ServiceClientError("not found", status_code=404)

    def _payload(self, **overrides):
        data = {
            "full_name": "Иван Иванов",
            "email": "ivan@example.com",
            "phone": "+7 777 123 45 67",
            "iin": RAW_IIN,
            "password": "securepass123",
            "repeat_password": "securepass123",
            "role": Role.DONOR,
            "personal_data_consent": True,
        }
        data.update(overrides)
        return data

    def test_register_donor_success(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="ivan@example.com")
        self.assertTrue(check_password("securepass123", user.password))
        self.assertEqual(user.iin_hash, hmac_hash(RAW_IIN))
        self.assertEqual(user.iin_masked, mask_iin(RAW_IIN))
        self.assertNotEqual(user.iin_encrypted, RAW_IIN)
        self.assertNotEqual(user.phone_encrypted, "+7 777 123 45 67")
        self.assertNotIn(RAW_IIN, str(response.data))
        self.assertEqual(response.data["iin_masked"], mask_iin(RAW_IIN))

    def test_register_password_mismatch_rejected(self):
        response = self.client.post(
            self.url, self._payload(repeat_password="differentpass"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("repeat_password", response.data)

    def test_register_moderator_role_rejected(self):
        response = self.client.post(
            self.url, self._payload(email="mod@example.com", role=Role.MODERATOR), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email_rejected(self):
        self.client.post(self.url, self._payload(), format="json")
        response = self.client.post(
            self.url,
            self._payload(email="ivan@example.com", iin="870308301456"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_iin_rejected(self):
        self.client.post(self.url, self._payload(), format="json")
        response = self.client.post(
            self.url,
            self._payload(email="other@example.com"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("iin", response.data)

    @patch("identity.ecp_services.verification_client")
    def test_register_author_high_risk_goes_to_manual_review(self, mock_client):
        mock_client.return_value.post.return_value = {"blocked": True, "risk_score": 92}
        response = self.client.post(
            self.url,
            self._payload(email="fraud@example.com", role=Role.AUTHOR, iin="990101300999"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="fraud@example.com")
        self.assertEqual(user.status, UserStatus.MANUAL_REVIEW)
        event = OutboxEvent.objects.filter(event_type="user.manual_review_required", aggregate_id=str(user.id)).last()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["iin_hash"], user.iin_hash)
        self.assertNotIn("990101300999", str(event.payload))

    @patch("identity.ecp_services.verification_client")
    def test_register_donor_high_risk_iin_allowed(self, mock_client):
        mock_client.return_value.post.return_value = {"blocked": True, "risk_score": 92}
        response = self.client.post(
            self.url,
            self._payload(email="donor-fraud@example.com", iin="990101300999"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class LoginMeAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="securepass123",
            full_name="Тест Пользователь",
            role=Role.DONOR,
            iin=LOGIN_IIN,
            phone="+7 777 123 45 67",
        )

    def test_login_returns_jwt_tokens(self):
        response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        token = AccessToken(response.data["access"])
        self.assertEqual(token["iin_hash"], hmac_hash(LOGIN_IIN))
        self.assertNotIn("iin", token)

    def test_blocked_user_cannot_login(self):
        self.user.status = UserStatus.BLOCKED
        self.user.save(update_fields=["status"])
        response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_returns_current_user(self):
        login_response = self.client.post(
            "/api/auth/login",
            {"email": "user@example.com", "password": "securepass123"},
            format="json",
        )
        response = self.client.get(
            "/api/auth/me",
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@example.com")
        self.assertEqual(response.data["iin_masked"], mask_iin(LOGIN_IIN))
        self.assertNotIn(LOGIN_IIN, str(response.data))
        self.assertEqual(response.data["phone"], "+7 777 123 45 67")

    def test_admin_list_does_not_expose_full_iin(self):
        admin = User.objects.create_user(
            email="admin@example.com",
            password="securepass123",
            full_name="Админ",
            role=Role.ADMIN,
            iin="870308301456",
        )
        login_response = self.client.post(
            "/api/auth/login",
            {"email": admin.email, "password": "securepass123"},
            format="json",
        )
        response = self.client.get(
            "/api/admin/users/",
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = str(response.data)
        self.assertNotIn(LOGIN_IIN, payload)
        self.assertNotIn("870308301456", payload)

    def test_health(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service"], "identity")


class SensitiveValueRedactionTestCase(APITestCase):
    def test_logs_redact_raw_iin(self):
        message = redact_sensitive("lookup iin=880420301999 failed for 880420301999")
        self.assertNotIn("880420301999", message)
        self.assertIn("[REDACTED_IIN]", message)

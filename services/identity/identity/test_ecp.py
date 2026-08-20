from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.constants import Role, UserStatus
from ekomek_common.masking import mask_iin

from .models import User

RAW_IIN = "880420301999"


def ecp_verify_payload(iin=RAW_IIN, **overrides):
    payload = {
        "verification_id": 9,
        "iin": iin,
        "iin_masked": mask_iin(iin),
        "full_name": "ИВАНОВ ИВАН ИВАНОВИЧ",
        "birth_date": "1988-04-20",
        "certificate_type": "individual",
        "serial_number": "aa",
        "issuer": "NCA RK",
        "valid_from": "2024-01-01T00:00:00+00:00",
        "valid_to": "2027-01-01T00:00:00+00:00",
    }
    payload.update(overrides)
    return payload


class EcpRegistrationAPITestCase(APITestCase):
    def _verification_post(self, path, json=None, **kwargs):
        if "ecp/verify" in path:
            return ecp_verify_payload()
        return {"blocked": False, "risk_score": 8}

    def test_challenge_is_short_lived(self):
        response = self.client.post("/api/auth/ecp/challenge", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("challenge_id", response.data)
        self.assertIn("challenge", response.data)
        self.assertLessEqual(response.data["expires_in"], 300)

    @patch("identity.ecp_services.verification_client")
    def test_verify_autofills_and_hides_full_iin(self, mock_client):
        mock_client.return_value.post.side_effect = self._verification_post
        challenge = self.client.post("/api/auth/ecp/challenge", {}, format="json").data
        response = self.client.post(
            "/api/auth/ecp/verify",
            {"challenge_id": challenge["challenge_id"], "cms": "dGVzdA=="},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "ИВАНОВ ИВАН ИВАНОВИЧ")
        self.assertEqual(response.data["iin_masked"], mask_iin(RAW_IIN))
        self.assertNotIn("iin", response.data)
        self.assertNotIn(RAW_IIN, str(response.data))
        self.assertIn("ecp_session_token", response.data)
        self.assertEqual(response.data["locked_fields"], ["full_name", "iin", "birth_date"])
        reused = self.client.post(
            "/api/auth/ecp/verify",
            {"challenge_id": challenge["challenge_id"], "cms": "dGVzdA=="},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("identity.ecp_services.verification_client")
    def test_register_ecp_locks_fields_and_verifies(self, mock_client):
        mock_client.return_value.post.side_effect = self._verification_post
        challenge = self.client.post("/api/auth/ecp/challenge", {}, format="json").data
        verified = self.client.post(
            "/api/auth/ecp/verify",
            {"challenge_id": challenge["challenge_id"], "cms": "dGVzdA=="},
            format="json",
        ).data
        response = self.client.post(
            "/api/auth/register/ecp",
            {
                "ecp_session_token": verified["ecp_session_token"],
                "email": "ecp@example.com",
                "phone": "+7 777 123 45 67",
                "password": "securepass123",
                "repeat_password": "securepass123",
                "role": Role.DONOR,
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email="ecp@example.com")
        self.assertEqual(user.full_name, "ИВАНОВ ИВАН ИВАНОВИЧ")
        self.assertEqual(user.status, UserStatus.ECP_VERIFIED)
        self.assertEqual(user.ecp_locked_fields, ["full_name", "iin", "birth_date"])
        self.assertNotIn(RAW_IIN, str(response.data))

    def test_register_ecp_rejects_moderator_role(self):
        response = self.client.post(
            "/api/auth/register/ecp",
            {
                "ecp_session_token": "x",
                "email": "mod@example.com",
                "phone": "+7 777 123 45 67",
                "password": "securepass123",
                "repeat_password": "securepass123",
                "role": Role.MODERATOR,
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("identity.ecp_services.verification_client")
    def test_high_risk_author_gets_manual_review(self, mock_client):
        def post(path, json=None, **kwargs):
            if "ecp/verify" in path:
                return ecp_verify_payload(iin="990101300999")
            return {"blocked": True, "risk_score": 92}

        mock_client.return_value.post.side_effect = post
        challenge = self.client.post("/api/auth/ecp/challenge", {}, format="json").data
        verified = self.client.post(
            "/api/auth/ecp/verify",
            {"challenge_id": challenge["challenge_id"], "cms": "dGVzdA=="},
            format="json",
        ).data
        response = self.client.post(
            "/api/auth/register/ecp",
            {
                "ecp_session_token": verified["ecp_session_token"],
                "email": "author-risk@example.com",
                "phone": "+7 777 123 45 67",
                "password": "securepass123",
                "repeat_password": "securepass123",
                "role": Role.AUTHOR,
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email="author-risk@example.com")
        self.assertEqual(user.status, UserStatus.MANUAL_REVIEW)
        self.assertFalse(user.can_create_public_fundraiser)

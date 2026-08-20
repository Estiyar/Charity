from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role
from ekomek_common.crypto import hmac_hash
from ekomek_common.masking import mask_iin

from .models import FraudProfile, Gender, MedicalDiagnosis, MedicalRecord, RiskLevel

RECIPIENT_IIN = "850315301234"
HIGH_RISK_IIN = "990101300999"


class VerificationAPITestCase(APITestCase):
    def setUp(self):
        self.record = MedicalRecord(
            full_name="Айгуль Смагулова",
            birth_date=date(1985, 3, 15),
            gender=Gender.FEMALE,
            city="Алматы",
            clinic="Городская поликлиника №5",
        )
        self.record.assign_iin(RECIPIENT_IIN)
        self.record.save()
        MedicalDiagnosis.objects.create(
            record=self.record,
            name="Онкология",
            stage="II",
            diagnosed_date=date(2024, 6, 10),
        )
        self.profile = FraudProfile(
            full_name="Ерболат Мукашев",
            risk_score=92,
            risk_level=RiskLevel.HIGH,
            reasons=["fraud"],
        )
        self.profile.assign_iin(HIGH_RISK_IIN)
        self.profile.save()
        self.author = make_principal(1, Role.AUTHOR, email="author@test.com")

    def test_health(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)

    def test_medregistry_requires_author(self):
        response = self.client.post("/api/medregistry/lookup/", {"iin": RECIPIENT_IIN}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_author_can_read_medregistry(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            "/api/medregistry/lookup/", {"iin": RECIPIENT_IIN}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Айгуль Смагулова")
        self.assertEqual(response.data["iin_masked"], mask_iin(RECIPIENT_IIN))
        self.assertNotIn("iin", response.data)
        self.assertNotIn(RECIPIENT_IIN, str(response.data))

    def test_internal_antifraud_blocked_flag(self):
        response = self.client.post(
            "/internal/antifraud/lookup/",
            {"iin": HIGH_RISK_IIN},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["blocked"])
        self.assertNotIn(HIGH_RISK_IIN, str(response.data))

    def test_internal_antifraud_by_hash(self):
        response = self.client.get(
            f"/internal/antifraud/hash/{hmac_hash(HIGH_RISK_IIN)}/",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["blocked"])

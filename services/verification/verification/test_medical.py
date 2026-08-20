from datetime import date

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.masking import mask_iin

from .models import Gender, MedicalDiagnosis, MedicalRecord

RECIPIENT_IIN = "850315301234"
MISSING_IIN = "880420301999"


class RecipientVerifyAPITestCase(APITestCase):
    def setUp(self):
        record = MedicalRecord(
            full_name="Айгуль Смагулова",
            birth_date=date(1985, 3, 15),
            gender=Gender.FEMALE,
            city="Алматы",
            clinic="Городская поликлиника №5",
        )
        record.assign_iin(RECIPIENT_IIN)
        record.save()
        MedicalDiagnosis.objects.create(
            record=record,
            name="Онкология",
            stage="II",
            diagnosed_date=date(2024, 6, 10),
        )

    def test_dev_adapter_autofills_medical_fields(self):
        response = self.client.post(
            "/internal/recipient/verify/",
            {"iin": RECIPIENT_IIN, "full_name": "Айгуль Смагулова"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["full_name"], "Айгуль Смагулова")
        self.assertEqual(response.data["city"], "Алматы")
        self.assertEqual(response.data["clinic"], "Городская поликлиника №5")
        self.assertEqual(response.data["diagnosis"], "Онкология")
        self.assertEqual(response.data["gender"], "female")
        self.assertTrue(response.data["age"])
        self.assertEqual(response.data["iin_masked"], mask_iin(RECIPIENT_IIN))
        self.assertFalse(response.data["requires_manual_review"])

    def test_missing_record_requires_manual_review(self):
        response = self.client.post(
            "/internal/recipient/verify/",
            {"iin": MISSING_IIN},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["incomplete"])
        self.assertTrue(response.data["requires_manual_review"])
        self.assertIn("medical_record_not_found", response.data["review_reasons"])
        self.assertEqual(response.data["diagnosis"], "")

    @override_settings(MEDICAL_SOURCE_ADAPTER="official", MEDICAL_SOURCE_URL="")
    def test_unconfigured_official_source_is_unavailable(self):
        response = self.client.post(
            "/internal/recipient/verify/",
            {"iin": RECIPIENT_IIN},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["unavailable"])
        self.assertTrue(response.data["requires_manual_review"])
        self.assertIn("medical_source_unavailable", response.data["review_reasons"])
        self.assertNotEqual(response.data["full_name"], "Айгуль Смагулова")

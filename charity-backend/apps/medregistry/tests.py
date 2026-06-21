from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Gender, MedicalDiagnosis, MedicalRecord

User = get_user_model()


class MedregistryAPITestCase(APITestCase):
    databases = {"default", "medregistry", "antifraud"}

    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор Тест",
            role="author",
            iin="880420301999",
        )
        self.donor = User.objects.create_user(
            email="donor@example.com",
            password="securepass123",
            full_name="Донор Тест",
            role="donor",
            iin="930615402345",
        )
        self.record = MedicalRecord.objects.create(
            iin="850315301234",
            full_name="Айгуль Смагулова",
            birth_date=date(1985, 3, 15),
            gender=Gender.FEMALE,
            city="Алматы",
            clinic="Городская поликлиника №5",
        )
        MedicalDiagnosis.objects.create(
            record=self.record,
            name="Онкология",
            stage="II",
            diagnosed_date=date(2024, 6, 10),
        )

    def test_get_record_by_iin(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/medregistry/850315301234/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Айгуль Смагулова")
        self.assertEqual(len(response.data["diagnoses"]), 1)
        self.assertEqual(response.data["diagnoses"][0]["name"], "Онкология")

    def test_get_record_not_found(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/medregistry/111111111111/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_record_invalid_iin(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/medregistry/123/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_record_requires_author_role(self):
        self.client.force_authenticate(user=self.donor)
        response = self.client.get("/api/medregistry/850315301234/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_record_requires_authentication(self):
        response = self.client.get("/api/medregistry/850315301234/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

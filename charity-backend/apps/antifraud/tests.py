from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import FraudProfile, RiskLevel

User = get_user_model()


class AntifraudAPITestCase(APITestCase):
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
        FraudProfile.objects.create(
            iin="850315301234",
            full_name="Айгуль Смагулова",
            risk_score=12,
            risk_level=RiskLevel.LOW,
            reasons=["Проверенный получатель помощи"],
        )
        FraudProfile.objects.create(
            iin="990101300999",
            full_name="Ерболат Мукашев",
            risk_score=92,
            risk_level=RiskLevel.HIGH,
            reasons=["Множественные мошеннические заявки"],
        )

    def test_get_risk_by_iin(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/antifraud/850315301234/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["risk_level"], RiskLevel.LOW)
        self.assertEqual(response.data["risk_score"], 12)

    def test_get_high_risk_profile(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/antifraud/990101300999/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["risk_level"], RiskLevel.HIGH)

    def test_get_profile_not_found(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/antifraud/111111111111/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_profile_invalid_iin(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/antifraud/123/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_profile_requires_author_role(self):
        self.client.force_authenticate(user=self.donor)
        response = self.client.get("/api/antifraud/850315301234/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

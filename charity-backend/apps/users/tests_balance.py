from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import BalanceTransaction, BalanceTransactionType, Role

User = get_user_model()


class BalanceAPITestCase(APITestCase):
    def setUp(self):
        self.donor = User.objects.create_user(
            email="balance-donor@example.com",
            password="securepass123",
            full_name="Донор Баланс",
            role=Role.DONOR,
        )

    def test_balance_starts_at_zero(self):
        self.client.force_authenticate(user=self.donor)
        response = self.client.get("/api/auth/balance/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["balance"], "0.00")
        self.assertEqual(response.data["transactions"], [])

    def test_withdraw_full_balance(self):
        self.donor.balance = Decimal("15000.00")
        self.donor.save(update_fields=["balance"])
        self.client.force_authenticate(user=self.donor)

        response = self.client.post("/api/auth/balance/withdraw/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Заявка на вывод принята")
        self.assertEqual(response.data["balance"], "0.00")
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.balance, Decimal("0.00"))
        self.assertEqual(
            BalanceTransaction.objects.filter(
                user=self.donor,
                transaction_type=BalanceTransactionType.WITHDRAW_OUT,
            ).count(),
            1,
        )

    def test_withdraw_rejects_empty_balance(self):
        self.client.force_authenticate(user=self.donor)
        response = self.client.post("/api/auth/balance/withdraw/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdraw_partial_amount(self):
        self.donor.balance = Decimal("10000.00")
        self.donor.save(update_fields=["balance"])
        self.client.force_authenticate(user=self.donor)

        response = self.client.post(
            "/api/auth/balance/withdraw/",
            {"amount": "4000.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["balance"], "6000.00")

    def test_withdraw_requires_authentication(self):
        response = self.client.post("/api/auth/balance/withdraw/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role
from ekomek_common.crypto import hmac_hash

from .models import Donation


class PaymentsAPITestCase(APITestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)

    @patch("payments.services.cards_client")
    def test_donate_active_card(self, mock_cards):
        card = {
            "id": 1,
            "status": "active",
            "author_id": 99,
            "iin_hash": hmac_hash("111111111111"),
            "full_name": "Test",
            "collected_amount": "0",
        }
        mock_cards.return_value.get.return_value = card
        mock_cards.return_value.post.return_value = {**card, "collected_amount": "1000"}
        response = self.client.post(
            "/api/cards/1/donate/",
            {
                "amount": "1000.00",
                "donor_name": "Донор",
                "contact": "donor@test.com",
                "payment_method": "card",
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Donation.objects.count(), 1)
        donation = Donation.objects.get()
        self.assertNotEqual(donation.payment_status, "success")
        self.assertTrue(donation.redirect_url)

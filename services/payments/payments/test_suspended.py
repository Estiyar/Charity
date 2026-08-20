from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.crypto import hmac_hash

from .models import Donation, PaymentStatus
from .providers.dev import DevPaymentAdapter
from .suspend_handlers import cancel_open_donations_for_card, handle_card_suspended


def active_card():
    return {
        "id": 1,
        "status": "active",
        "author_id": 99,
        "iin_hash": hmac_hash("111111111111"),
        "full_name": "Test",
        "collected_amount": "0",
    }


@override_settings(PAYMENT_ADAPTER="dev")
class SuspendedCardPaymentsTest(APITestCase):
    def setUp(self):
        cards_patcher = patch("payments.services.cards_client")
        collect_patcher = patch("payments.payment_flow.cards_client")
        self.mock_cards = cards_patcher.start()
        self.mock_collect = collect_patcher.start()
        self.addCleanup(cards_patcher.stop)
        self.addCleanup(collect_patcher.stop)
        self.mock_cards.return_value.get.return_value = active_card()
        self.mock_collect.return_value.post.return_value = {**active_card(), "collected_amount": "1000.00"}

    def _donate(self):
        return self.client.post(
            "/api/cards/1/donate/",
            {
                "amount": "1000.00",
                "donor_name": "Донор",
                "email": "donor@test.com",
                "phone": "+77001112233",
                "payment_method": "card",
                "personal_data_consent": True,
                "idempotency_key": "idem-suspend",
            },
            format="json",
        )

    def test_donation_rejected_for_suspended_card(self):
        self.mock_cards.return_value.get.return_value = {**active_card(), "status": "suspended"}
        response = self._donate()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_open_donations_canceled_on_suspend_event(self):
        created = self._donate()
        donation = Donation.objects.get(pk=created.data["donation"]["id"])
        self.assertEqual(donation.payment_status, PaymentStatus.PROCESSING)
        handle_card_suspended({"card_id": 1, "reason": "Проверка"})
        donation.refresh_from_db()
        self.assertEqual(donation.payment_status, PaymentStatus.CANCELED)

    def test_success_webhook_blocked_when_card_suspended(self):
        created = self._donate()
        donation = Donation.objects.get(pk=created.data["donation"]["id"])
        self.mock_collect.return_value.get.return_value = {**active_card(), "status": "suspended"}
        self.mock_collect.return_value.post.reset_mock()
        payload = {
            "order_id": str(donation.id),
            "provider_payment_id": donation.provider_payment_id,
            "amount": str(donation.amount),
            "currency": donation.currency,
            "card_id": donation.card_id,
            "status": "success",
            "failed_reason": "",
        }
        body, signature = DevPaymentAdapter().sign_payload(payload)
        response = self.client.post(
            "/api/payments/webhook/dev",
            data=body,
            content_type="application/json",
            HTTP_X_DEV_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        donation.refresh_from_db()
        self.assertEqual(donation.payment_status, PaymentStatus.CANCELED)
        self.mock_collect.return_value.post.assert_not_called()

    def test_cancel_open_donations_helper(self):
        Donation.objects.create(
            card_id=7,
            card_name="X",
            donor_name="A",
            amount="100.00",
            payment_status=PaymentStatus.PROCESSING,
            idempotency_key="k1",
        )
        cancel_open_donations_for_card(7, "stopped")
        self.assertEqual(Donation.objects.get().payment_status, PaymentStatus.CANCELED)

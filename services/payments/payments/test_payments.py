from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.crypto import hmac_hash
from ekomek_common.outbox_app.models import OutboxEvent

from .models import Donation, LedgerEntry, PaymentEvent, PaymentStatus
from .providers.dev import DevPaymentAdapter
from .providers.freedompay import FreedomPayAdapter, make_freedompay_signature


def active_card():
    return {
        "id": 1,
        "status": "active",
        "author_id": 99,
        "iin_hash": hmac_hash("111111111111"),
        "full_name": "Test",
        "collected_amount": "0",
    }


class PaymentWorkflowTestCase(APITestCase):
    def setUp(self):
        cards_patcher = patch("payments.services.cards_client")
        collect_patcher = patch("payments.payment_flow.cards_client")
        self.mock_cards = cards_patcher.start()
        self.mock_collect = collect_patcher.start()
        self.addCleanup(cards_patcher.stop)
        self.addCleanup(collect_patcher.stop)
        self.mock_cards.return_value.get.return_value = active_card()
        self.mock_collect.return_value.get.return_value = active_card()
        self.mock_collect.return_value.post.return_value = {**active_card(), "collected_amount": "1000.00"}

    def _donate(self, **overrides):
        payload = {
            "amount": "1000.00",
            "donor_name": "Донор",
            "email": "donor@test.com",
            "phone": "+77001112233",
            "payment_method": "card",
            "personal_data_consent": True,
            "idempotency_key": "idem-1",
        }
        payload.update(overrides)
        return self.client.post("/api/cards/1/donate/", payload, format="json")

    def _sign_dev(self, donation, status_name="success", **overrides):
        payload = {
            "order_id": str(donation.id),
            "provider_payment_id": donation.provider_payment_id,
            "amount": str(donation.amount),
            "currency": donation.currency,
            "card_id": donation.card_id,
            "status": status_name,
            "failed_reason": "",
        }
        payload.update(overrides)
        body, signature = DevPaymentAdapter().sign_payload(payload)
        return payload, body, signature

    def test_session_creates_pending_payment_without_collecting(self):
        response = self._donate()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        donation = Donation.objects.get()
        self.assertEqual(donation.payment_status, PaymentStatus.PROCESSING)
        self.assertTrue(donation.redirect_url)
        self.assertEqual(donation.provider, "dev")
        self.mock_collect.return_value.post.assert_not_called()
        self.assertTrue(OutboxEvent.objects.filter(event_type="payment.created").exists())

    def test_idempotency_key_returns_same_session(self):
        first = self._donate()
        second = self._donate()
        self.assertEqual(first.data["donation"]["id"], second.data["donation"]["id"])
        self.assertEqual(Donation.objects.count(), 1)

    def test_client_cannot_set_success(self):
        created = self._donate()
        payment_id = created.data["donation"]["id"]
        response = self.client.patch(f"/api/payments/{payment_id}", {"payment_status": "success"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Donation.objects.get().payment_status, PaymentStatus.PROCESSING)

    def test_signed_webhook_credits_once(self):
        created = self._donate()
        donation = Donation.objects.get(pk=created.data["donation"]["id"])
        payload, body, signature = self._sign_dev(donation)
        response = self.client.post(
            "/api/payments/webhook/dev",
            data=body,
            content_type="application/json",
            HTTP_X_DEV_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        donation.refresh_from_db()
        self.assertEqual(donation.payment_status, PaymentStatus.SUCCESS)
        self.assertTrue(donation.collected_applied)
        self.assertEqual(LedgerEntry.objects.count(), 1)
        self.mock_collect.return_value.post.assert_called_once()
        duplicate = self.client.post(
            "/api/payments/webhook/dev",
            data=body,
            content_type="application/json",
            HTTP_X_DEV_SIGNATURE=signature,
        )
        self.assertEqual(duplicate.status_code, status.HTTP_200_OK)
        self.assertEqual(LedgerEntry.objects.count(), 1)
        self.mock_collect.return_value.post.assert_called_once()
        self.assertEqual(
            Donation.objects.filter(payment_status=PaymentStatus.SUCCESS).count(),
            LedgerEntry.objects.count(),
        )
        self.assertTrue(OutboxEvent.objects.filter(event_type="payment.succeeded").exists())
        self.assertTrue(PaymentEvent.objects.filter(donation=donation, event_type="succeeded").exists())

    def test_invalid_signature_rejected(self):
        created = self._donate()
        donation = Donation.objects.get(pk=created.data["donation"]["id"])
        payload, body, _signature = self._sign_dev(donation)
        response = self.client.post(
            "/api/payments/webhook/dev",
            data=body,
            content_type="application/json",
            HTTP_X_DEV_SIGNATURE="deadbeef",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Donation.objects.get().payment_status, PaymentStatus.PROCESSING)
        self.mock_collect.return_value.post.assert_not_called()

    def test_amount_mismatch_rejected(self):
        created = self._donate()
        donation = Donation.objects.get(pk=created.data["donation"]["id"])
        payload, body, signature = self._sign_dev(donation, amount="5.00")
        response = self.client.post(
            "/api/payments/webhook/dev",
            data=body,
            content_type="application/json",
            HTTP_X_DEV_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mock_collect.return_value.post.assert_not_called()

    def test_failed_webhook_does_not_collect(self):
        created = self._donate()
        donation = Donation.objects.get(pk=created.data["donation"]["id"])
        payload, body, signature = self._sign_dev(donation, status_name="failed")
        response = self.client.post(
            "/api/payments/webhook/dev",
            data=body,
            content_type="application/json",
            HTTP_X_DEV_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Donation.objects.get().payment_status, PaymentStatus.FAILED)
        self.mock_collect.return_value.post.assert_not_called()
        self.assertTrue(OutboxEvent.objects.filter(event_type="payment.failed").exists())

    def test_browser_callback_cannot_mark_success(self):
        created = self._donate()
        payment_id = created.data["donation"]["id"]
        response = self.client.get(f"/api/payments/callback?payment={payment_id}&outcome=success")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Donation.objects.get().payment_status, PaymentStatus.PROCESSING)

    @override_settings(PAYMENT_ADAPTER="freedompay", FREEDOMPAY_MERCHANT_ID="", FREEDOMPAY_SECRET="")
    def test_freedompay_without_credentials_is_unavailable(self):
        response = self._donate(idempotency_key="fp-1")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @override_settings(FREEDOMPAY_MERCHANT_ID="123", FREEDOMPAY_SECRET="secret")
    def test_freedompay_signature_roundtrip(self):
        params = {
            "pg_order_id": "10",
            "pg_payment_id": "abc",
            "pg_amount": "1000.00",
            "pg_currency": "KZT",
            "pg_result": "1",
            "pg_param1": "1",
            "pg_salt": "salt",
        }
        params["pg_sig"] = make_freedompay_signature("freedompay", params, "secret")
        result = FreedomPayAdapter().parse_result(params, script_name="freedompay")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.provider_payment_id, "abc")
        params["pg_sig"] = "00"
        with self.assertRaises(Exception):
            FreedomPayAdapter().parse_result(params, script_name="freedompay")

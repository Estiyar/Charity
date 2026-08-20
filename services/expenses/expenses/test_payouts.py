import json
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role

from .events import on_payment_succeeded
from .ledger_services import ledger_totals
from .models import LedgerEntry
from .payout_models import Invoice, InvoiceStatus, Payout, PayoutStatus
from .payout_providers.dev import DevPayoutAdapter
from .reconcile import reconcile_card


class ClinicPayoutTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com")
        self.card = {
            "id": 1,
            "author_id": 11,
            "status": "active",
            "full_name": "Получатель",
            "collected_amount": "10000.00",
            "target_amount": "20000.00",
            "escrow_spent": "0",
            "escrow_pending": "0",
        }
        patcher = patch("expenses.workflow.cards_client")
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        mocked.return_value.get.return_value = self.card

        def post_card(path, json=None, **kwargs):
            if json and "spent" in json:
                self.card["escrow_spent"] = str(json["spent"])
                self.card["escrow_pending"] = str(json.get("pending") or 0)
            return {}

        mocked.return_value.post.side_effect = post_card
        on_payment_succeeded({"donation_id": 21, "card_id": 1, "amount": "10000.00"})

    def _invoice_payload(self, **overrides):
        payload = {
            "date": "2026-03-01",
            "amount": "1500.00",
            "organization_name": "Клиника Астана",
            "organization_bin": "123456789012",
            "iban": "KZ86125KZT5004100100",
            "bank_name": "Halyk Bank",
            "file": SimpleUploadedFile("invoice.pdf", b"%PDF-invoice", content_type="application/pdf"),
        }
        payload.update(overrides)
        return payload

    def _create_invoice(self):
        self.client.force_authenticate(self.author)
        return self.client.post("/api/cards/1/invoices/", self._invoice_payload(), format="multipart")

    def _signed_webhook(self, payout, status="succeeded"):
        payload = {
            "payout_id": str(payout.id),
            "provider_payout_id": payout.provider_payout_id,
            "amount": str(payout.amount),
            "currency": payout.currency,
            "card_id": payout.card_id,
            "status": status,
        }
        body, signature = DevPayoutAdapter().sign_payload(payload)
        return self.client.generic(
            "POST",
            "/api/payouts/webhook/dev",
            body,
            content_type="application/json",
            HTTP_X_DEV_SIGNATURE=signature,
        )

    def test_verify_then_signed_callback_writes_ledger_once(self):
        created = self._create_invoice()
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["status"], InvoiceStatus.PENDING_VERIFICATION)
        self.assertNotIn("KZ86125KZT5004100100", json.dumps(created.data))
        self.client.force_authenticate(self.moderator)
        verified = self.client.post(f"/api/invoices/{created.data['id']}/verify/", {"comment": "клиника подтверждена"}, format="json")
        self.assertEqual(verified.status_code, 200, verified.data)
        self.assertEqual(verified.data["status"], InvoiceStatus.VERIFIED)
        payout = Payout.objects.get(invoice_id=created.data["id"])
        self.assertEqual(payout.status, PayoutStatus.PROCESSING)
        first = self._signed_webhook(payout)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(Payout.objects.get(pk=payout.id).status, PayoutStatus.SUCCEEDED)
        self.assertEqual(Invoice.objects.get(pk=created.data["id"]).status, InvoiceStatus.PAID)
        self.assertEqual(LedgerEntry.objects.filter(entry_type="payout").count(), 1)
        second = self._signed_webhook(payout)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(LedgerEntry.objects.filter(entry_type="payout").count(), 1)
        self.assertEqual(ledger_totals(1)["total_direct_payouts"], Decimal("1500.00"))

    def test_unsigned_webhook_is_rejected(self):
        created = self._create_invoice()
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/invoices/{created.data['id']}/verify/", {"comment": "ок"}, format="json")
        payout = Payout.objects.get()
        response = self.client.post(
            "/api/payouts/webhook/dev",
            {
                "payout_id": payout.id,
                "provider_payout_id": payout.provider_payout_id,
                "amount": str(payout.amount),
                "currency": "KZT",
                "card_id": 1,
                "status": "succeeded",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payout.objects.get().status, PayoutStatus.PROCESSING)
        self.assertEqual(LedgerEntry.objects.filter(entry_type="payout").count(), 0)

    def test_frontend_cannot_mark_payout_or_invoice_paid(self):
        created = self._create_invoice()
        self.client.force_authenticate(self.author)
        invoice_patch = self.client.post(f"/api/invoices/{created.data['id']}/", {"status": "paid"}, format="json")
        self.assertEqual(invoice_patch.status_code, 405)
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/invoices/{created.data['id']}/verify/", {"comment": "ок"}, format="json")
        payout = Payout.objects.get()
        self.client.force_authenticate(self.author)
        payout_patch = self.client.post(f"/api/payouts/{payout.id}/", {"status": "paid"}, format="json")
        self.assertEqual(payout_patch.status_code, 405)
        self.assertEqual(Payout.objects.get().status, PayoutStatus.PROCESSING)
        author_payout = self.client.post("/api/payouts/", {"invoice_id": created.data["id"]}, format="json")
        self.assertEqual(author_payout.status_code, 403)

    def test_public_report_shows_payout_without_bank_details(self):
        created = self._create_invoice()
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/invoices/{created.data['id']}/verify/", {"comment": "ок"}, format="json")
        self._signed_webhook(Payout.objects.get())
        self.client.force_authenticate(None)
        report = self.client.get("/api/cards/1/expenses/public/")
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual(Decimal(str(report.data["total_direct_payouts"])), Decimal("1500.00"))
        payout_rows = [item for item in report.data["expenses"] if item.get("kind") == "payout"]
        self.assertEqual(len(payout_rows), 1)
        self.assertEqual(payout_rows[0]["status"], "paid")
        self.assertNotIn("KZ86125KZT5004100100", str(report.data))
        self.assertNotIn("123456789012", str(report.data))
        original = self.client.get(f"/api/invoices/{created.data['id']}/original/")
        self.assertEqual(original.status_code, 404)

    def test_reject_requires_comment_and_does_not_pay(self):
        created = self._create_invoice()
        self.client.force_authenticate(self.moderator)
        denied = self.client.post(f"/api/invoices/{created.data['id']}/reject/", {"comment": ""}, format="json")
        self.assertEqual(denied.status_code, 400)
        self.client.post(f"/api/invoices/{created.data['id']}/reject/", {"comment": "реквизиты неверны"}, format="json")
        self.assertEqual(Payout.objects.count(), 0)
        self.assertEqual(Invoice.objects.get().status, InvoiceStatus.REJECTED)

    def test_invoice_over_escrow_rejected(self):
        self.client.force_authenticate(self.author)
        response = self.client.post(
            "/api/cards/1/invoices/",
            self._invoice_payload(amount="20000.00"),
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_reconciliation_matches_after_payout(self):
        created = self._create_invoice()
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/invoices/{created.data['id']}/verify/", {"comment": "ок"}, format="json")
        self._signed_webhook(Payout.objects.get())
        report = reconcile_card(1)
        self.assertTrue(report.matched, report.differences)

    def test_payout_create_is_idempotent(self):
        created = self._create_invoice()
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/invoices/{created.data['id']}/verify/", {"comment": "ок"}, format="json")
        first = self.client.post("/api/payouts/", {"invoice_id": created.data["id"]}, format="json")
        second = self.client.post("/api/payouts/", {"invoice_id": created.data["id"]}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.data["id"], first.data["id"])
        self.assertEqual(Payout.objects.count(), 1)

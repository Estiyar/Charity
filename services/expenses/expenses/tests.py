from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role

from .events import on_payment_succeeded, on_redistribution_choice
from .ledger_services import ledger_totals, record_ledger_entry
from .models import Expense, ExpenseDecisionEvent, ExpenseStatus, LedgerEntry
from .reconcile import reconcile_card
from .tasks import reconcile_ledgers


class ExpenseWorkflowTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        self.other = make_principal(12, Role.AUTHOR, email="other@test.com")
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

    def _payload(self, **overrides):
        payload = {
            "date": "2026-01-15",
            "purpose": "Лекарства",
            "amount": "1000.00",
            "category": "medicine",
        }
        payload.update(overrides)
        return payload

    def _create(self, **overrides):
        self.client.force_authenticate(self.author)
        data = self._payload(**overrides)
        uploaded = data.pop("file", None)
        body = {**data}
        if uploaded is not None:
            body["file"] = uploaded
        return self.client.post("/api/cards/1/expenses/", body, format="multipart")

    def test_submit_approve_writes_ledger_once(self):
        created = self._create()
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["status"], ExpenseStatus.PENDING_REVIEW)
        expense_id = created.data["id"]
        self.client.force_authenticate(self.moderator)
        first = self.client.post(f"/api/expenses/{expense_id}/approve/", {"comment": "ок"}, format="json")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["status"], ExpenseStatus.APPROVED)
        self.assertEqual(LedgerEntry.objects.filter(source_type="expense").count(), 1)
        second = self.client.post(f"/api/expenses/{expense_id}/approve/", {"comment": "повтор"}, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(LedgerEntry.objects.filter(source_type="expense").count(), 1)

    def test_payment_event_is_idempotent(self):
        payload = {"donation_id": 9, "card_id": 1, "amount": "2500.00", "currency": "KZT"}
        on_payment_succeeded(payload)
        on_payment_succeeded(payload)
        self.assertEqual(LedgerEntry.objects.filter(entry_type="donation").count(), 1)
        self.assertEqual(LedgerEntry.objects.get().amount, Decimal("2500.00"))

    def test_public_report_hides_sensitive_receipt(self):
        iin_file = SimpleUploadedFile("scan-850315301234.pdf", b"%PDF-850315301234", content_type="application/pdf")
        created = self._create(purpose="Оплата 850315301234", file=iin_file)
        expense_id = created.data["id"]
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/expenses/{expense_id}/approve/", {"comment": "ок"}, format="json")
        on_payment_succeeded({"donation_id": 3, "card_id": 1, "amount": "10000.00"})
        self.client.force_authenticate(None)
        report = self.client.get("/api/cards/1/expenses/public/")
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual(Decimal(str(report.data["total_collected"])), Decimal("10000.00"))
        self.assertEqual(Decimal(str(report.data["total_confirmed_expenses"])), Decimal("1000.00"))
        self.assertEqual(report.data["expenses"][0]["category"], "medicine")
        self.assertEqual(report.data["expenses"][0]["status"], ExpenseStatus.APPROVED)
        self.assertIn("available_balance", report.data)
        self.assertIn("remaining_target", report.data)
        self.assertIn("total_pending_expenses", report.data)
        self.assertIn("total_direct_payouts", report.data)
        self.assertNotIn("850315301234", str(report.data))
        self.assertIsNone(report.data["expenses"][0].get("original_url"))
        self.assertNotIn("original_file", report.data["expenses"][0])
        original = self.client.get(f"/api/expenses/{expense_id}/original/")
        self.assertEqual(original.status_code, 404)

    def test_revision_then_resubmit(self):
        created = self._create()
        expense_id = created.data["id"]
        self.client.force_authenticate(self.moderator)
        missing = self.client.post(f"/api/expenses/{expense_id}/request-revision/", {}, format="json")
        self.assertEqual(missing.status_code, 400)
        revised = self.client.post(
            f"/api/expenses/{expense_id}/request-revision/",
            {"revision_comment": "Нужен чек", "internal_comment": "сумма подозрительная"},
            format="json",
        )
        self.assertEqual(revised.status_code, 200, revised.data)
        self.assertEqual(revised.data["status"], ExpenseStatus.REVISION_REQUIRED)
        staff_types = {item["comment_type"] for item in revised.data["comments"]}
        self.assertEqual(staff_types, {"revision_comment", "internal_comment"})
        self.client.force_authenticate(self.author)
        author_view = self.client.get(f"/api/expenses/{expense_id}/")
        types = {item["comment_type"] for item in author_view.data["comments"]}
        self.assertEqual(types, {"revision_comment"})
        self.assertNotIn("сумма подозрительная", str(author_view.data))
        patched = self.client.patch(
            f"/api/expenses/{expense_id}/",
            {"purpose": "Лекарства с чеком"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200, patched.data)
        submitted = self.client.post(f"/api/expenses/{expense_id}/submit/")
        self.assertEqual(submitted.status_code, 200, submitted.data)
        self.assertEqual(submitted.data["status"], ExpenseStatus.PENDING_REVIEW)
        self.assertEqual(Expense.objects.get(pk=expense_id).moderator_comments.count(), 2)
        self.assertGreaterEqual(Expense.objects.get(pk=expense_id).decisions.count(), 3)

    def test_reject_requires_comment_and_does_not_post_ledger(self):
        created = self._create()
        expense_id = created.data["id"]
        self.client.force_authenticate(self.moderator)
        denied = self.client.post(f"/api/expenses/{expense_id}/reject/", {"comment": ""}, format="json")
        self.assertEqual(denied.status_code, 400)
        self.client.post(f"/api/expenses/{expense_id}/reject/", {"comment": "нет документов"}, format="json")
        self.assertEqual(LedgerEntry.objects.count(), 0)
        self.assertEqual(Expense.objects.get(pk=expense_id).status, ExpenseStatus.REJECTED)

    def test_exceeds_escrow_rejected(self):
        response = self._create(amount="20000.00")
        self.assertEqual(response.status_code, 400)

    def test_ledger_idempotency_and_immutability(self):
        first = record_ledger_entry(
            card_id=1,
            entry_type="donation",
            amount="10",
            source_type="donation",
            source_id=1,
            idempotency_key="donation:1:credit",
        )
        second = record_ledger_entry(
            card_id=1,
            entry_type="donation",
            amount="10",
            source_type="donation",
            source_id=1,
            idempotency_key="donation:1:credit",
        )
        self.assertEqual(first.id, second.id)
        with self.assertRaises(ValueError):
            first.amount = Decimal("99")
            first.save()
        event = ExpenseDecisionEvent(expense=Expense.objects.create(
            card_id=1,
            date=date(2026, 1, 1),
            purpose="x",
            amount=Decimal("1"),
        ), action="created")
        event.save()
        with self.assertRaises(ValueError):
            event.delete()

    def test_reconciliation_matches_after_donation_and_expense(self):
        on_payment_succeeded({"donation_id": 4, "card_id": 1, "amount": "10000.00"})
        created = self._create()
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/expenses/{created.data['id']}/approve/", {"comment": "ок"}, format="json")
        report = reconcile_card(1)
        self.assertTrue(report.matched, report.differences)

    def test_redistribution_writes_two_entries_once(self):
        payload = {
            "decision_id": 7,
            "choice": "redirect",
            "card_id": 1,
            "target_card_id": 2,
            "amount": "300.00",
        }
        on_redistribution_choice(payload)
        on_redistribution_choice(payload)
        self.assertEqual(LedgerEntry.objects.filter(source_type="redistribution").count(), 2)

    def test_frontend_cannot_mark_paid(self):
        created = self._create()
        self.client.force_authenticate(self.author)
        response = self.client.post(f"/api/expenses/{created.data['id']}/", {"status": "paid"}, format="json")
        self.assertEqual(response.status_code, 405)
        expense = Expense.objects.get(pk=created.data["id"])
        self.assertNotEqual(expense.status, ExpenseStatus.PAID)

    def test_pending_expenses_reserve_escrow(self):
        first = self._create(amount="7000.00")
        second = self._create(amount="4000.00")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 400)

    def test_ledger_reproduces_balances(self):
        on_payment_succeeded({"donation_id": 8, "card_id": 1, "amount": "10000.00"})
        created = self._create(amount="2500.00")
        self.client.force_authenticate(self.moderator)
        approved = self.client.post(f"/api/expenses/{created.data['id']}/approve/", {"comment": "ок"}, format="json")
        self.assertEqual(approved.status_code, 200, approved.data)
        totals = ledger_totals(1)
        self.assertEqual(totals["total_collected"], Decimal("10000.00"))
        self.assertEqual(totals["total_confirmed_expenses"], Decimal("2500.00"))
        self.assertEqual(totals["available_balance"], Decimal("7500.00"))

    def test_duplicate_donation_events_keep_single_credit(self):
        payload = {"donation_id": 55, "card_id": 1, "amount": "80.00"}
        on_payment_succeeded(payload)
        on_payment_succeeded(payload)
        on_payment_succeeded(payload)
        self.assertEqual(LedgerEntry.objects.filter(idempotency_key="donation:55:credit").count(), 1)
        self.assertEqual(ledger_totals(1)["total_collected"], Decimal("80.00"))

    def test_two_approved_expenses_both_post_ledger(self):
        first = self._create(amount="1000.00")
        second = self._create(amount="1500.00")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.client.force_authenticate(self.moderator)
        self.assertEqual(
            self.client.post(f"/api/expenses/{first.data['id']}/approve/", {"comment": "ок"}, format="json").status_code,
            200,
        )
        self.assertEqual(
            self.client.post(f"/api/expenses/{second.data['id']}/approve/", {"comment": "ок"}, format="json").status_code,
            200,
        )
        self.assertEqual(LedgerEntry.objects.filter(entry_type="expense").count(), 2)
        self.assertEqual(ledger_totals(1)["total_confirmed_expenses"], Decimal("2500.00"))

    def test_reconcile_job_writes_report(self):
        on_payment_succeeded({"donation_id": 6, "card_id": 1, "amount": "10000.00"})
        created = self._create()
        self.client.force_authenticate(self.moderator)
        self.client.post(f"/api/expenses/{created.data['id']}/approve/", {"comment": "ок"}, format="json")
        reconcile_ledgers()
        report = reconcile_card(1)
        self.assertTrue(report.matched, report.differences)


class ExpensesHealthTest(APITestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)

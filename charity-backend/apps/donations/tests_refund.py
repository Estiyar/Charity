from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus
from apps.donations.models import Donation, PaymentStatus, RefundChoice, RefundDecision, RefundDecisionStatus
from apps.donations.services import maybe_open_refund_period, process_expired_refund_deadlines
from apps.users.models import PlatformSettings, Role

User = get_user_model()


class RefundDecisionAPITestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@charity.test",
            password="securepass123",
            full_name="Админ",
            role=Role.ADMIN,
            is_staff=True,
        )
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор",
            role=Role.AUTHOR,
        )
        self.donor = User.objects.create_user(
            email="donor@example.com",
            password="securepass123",
            full_name="Иван Донор",
            role=Role.DONOR,
        )
        self.other_donor = User.objects.create_user(
            email="other@example.com",
            password="securepass123",
            full_name="Другой донор",
            role=Role.DONOR,
        )
        self.card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Завершаемый сбор",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("500000.00"),
            collected_amount=Decimal("110000.00"),
            end_date=date.today() + timedelta(days=30),
            status=CardStatus.ACTIVE,
        )
        self.target_card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Активный сбор",
            diagnosis="Онкология",
            city="Астана",
            target_amount=Decimal("300000.00"),
            collected_amount=Decimal("10000.00"),
            end_date=date.today() + timedelta(days=60),
            status=CardStatus.ACTIVE,
        )
        self.donation = Donation.objects.create(
            card=self.card,
            donor=self.donor,
            donor_name=self.donor.full_name,
            amount=Decimal("60000.00"),
            payment_method="card",
            payment_status=PaymentStatus.SUCCESS,
        )
        Donation.objects.create(
            card=self.card,
            donor=self.other_donor,
            donor_name=self.other_donor.full_name,
            amount=Decimal("40000.00"),
            payment_method="card",
            payment_status=PaymentStatus.SUCCESS,
        )
        Donation.objects.create(
            card=self.card,
            donor=None,
            donor_name="Аноним",
            amount=Decimal("10000.00"),
            payment_method="card",
            payment_status=PaymentStatus.SUCCESS,
        )
        PlatformSettings.get_solo()

    def _complete_card(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f"/api/admin/cards/{self.card.id}/set-status/",
            {"status": CardStatus.COMPLETED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.client.force_authenticate(user=None)

    def test_completed_card_with_leftover_opens_refund_period(self):
        self._complete_card()

        self.assertEqual(self.card.status, CardStatus.REDISTRIBUTION)
        decisions = RefundDecision.objects.filter(card=self.card)
        self.assertEqual(decisions.count(), 2)
        self.assertTrue(
            all(item.status == RefundDecisionStatus.PENDING for item in decisions)
        )
        donor_decision = decisions.get(donor=self.donor)
        self.assertEqual(donor_decision.share_amount, Decimal("60000.00"))

    def test_list_my_pending_refunds(self):
        self._complete_card()
        self.client.force_authenticate(user=self.donor)
        response = self.client.get("/api/refunds/my/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["share_amount"], "60000.00")
        self.assertEqual(response.data[0]["donation_id"], self.donation.id)
        self.assertEqual(len(response.data[0]["options"]), 3)
        self.assertTrue(len(response.data[0]["redirect_options"]) >= 1)

    def test_list_my_refund_history_after_choice(self):
        self._complete_card()
        decision = RefundDecision.objects.get(donor=self.donor)
        self.client.force_authenticate(user=self.donor)
        choose_response = self.client.post(
            f"/api/refunds/{decision.id}/choose/",
            {"choice": RefundChoice.KEEP},
            format="json",
        )
        self.assertEqual(choose_response.status_code, status.HTTP_200_OK)

        pending_response = self.client.get("/api/refunds/my/")
        self.assertEqual(len(pending_response.data), 0)

        history_response = self.client.get("/api/refunds/history/")
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(history_response.data), 1)
        self.assertEqual(history_response.data[0]["choice"], RefundChoice.KEEP)
        self.assertEqual(history_response.data[0]["status"], RefundDecisionStatus.DONE)
        self.assertIsNotNone(history_response.data[0]["resolved_at"])

    def test_refund_history_excludes_other_donors(self):
        self._complete_card()
        self.client.force_authenticate(user=self.other_donor)
        response = self.client.get("/api/refunds/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_choose_keep(self):
        self._complete_card()
        decision = RefundDecision.objects.get(donor=self.donor)
        self.client.force_authenticate(user=self.donor)
        response = self.client.post(
            f"/api/refunds/{decision.id}/choose/",
            {"choice": RefundChoice.KEEP},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decision.refresh_from_db()
        self.assertEqual(decision.status, RefundDecisionStatus.DONE)
        self.assertEqual(decision.choice, RefundChoice.KEEP)
        self.card.refresh_from_db()
        self.assertEqual(self.card.collected_amount, Decimal("110000.00"))

    def test_choose_refund_reduces_collected_amount(self):
        self._complete_card()
        decision = RefundDecision.objects.get(donor=self.donor)
        self.client.force_authenticate(user=self.donor)
        response = self.client.post(
            f"/api/refunds/{decision.id}/choose/",
            {"choice": RefundChoice.REFUND},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decision.refresh_from_db()
        self.assertEqual(decision.choice, RefundChoice.REFUND)
        self.card.refresh_from_db()
        self.assertEqual(self.card.collected_amount, Decimal("50000.00"))
        self.assertEqual(response.data["refund_payout"]["commission_percent"], 10)
        self.assertEqual(response.data["refund_payout"]["net_amount"], "54000.00")
        self.donor.refresh_from_db()
        self.assertEqual(self.donor.balance, Decimal("54000.00"))
        self.client.force_authenticate(user=self.donor)
        balance_response = self.client.get("/api/auth/balance/")
        self.assertEqual(balance_response.data["balance"], "54000.00")
        self.assertEqual(len(balance_response.data["transactions"]), 1)
        self.assertEqual(
            balance_response.data["transactions"][0]["transaction_type"],
            "refund_in",
        )

    def test_choose_redirect_moves_amount_to_target_card(self):
        self._complete_card()
        decision = RefundDecision.objects.get(donor=self.donor)
        self.client.force_authenticate(user=self.donor)
        response = self.client.post(
            f"/api/refunds/{decision.id}/choose/",
            {"choice": RefundChoice.REDIRECT, "target_card_id": self.target_card.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.target_card.refresh_from_db()
        self.assertEqual(self.card.collected_amount, Decimal("50000.00"))
        self.assertEqual(self.target_card.collected_amount, Decimal("70000.00"))

    def test_redirect_options_prefers_same_diagnosis(self):
        other_oncology = FundraisingCard.objects.create(
            author=self.author,
            full_name="Другой онкологический сбор",
            diagnosis="Онкология",
            city="Шымкент",
            target_amount=Decimal("200000.00"),
            collected_amount=Decimal("5000.00"),
            end_date=date.today() + timedelta(days=45),
            status=CardStatus.ACTIVE,
        )
        dcp_card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Сбор ДЦП",
            diagnosis="ДЦП",
            city="Алматы",
            target_amount=Decimal("200000.00"),
            collected_amount=Decimal("5000.00"),
            end_date=date.today() + timedelta(days=45),
            status=CardStatus.ACTIVE,
        )
        self._complete_card()
        self.client.force_authenticate(user=self.donor)
        response = self.client.get("/api/refunds/my/")

        option_ids = [item["id"] for item in response.data[0]["redirect_options"]]
        self.assertIn(self.target_card.id, option_ids)
        self.assertIn(other_oncology.id, option_ids)
        self.assertNotIn(dcp_card.id, option_ids)

    def test_redirect_fallback_to_all_active_when_no_same_diagnosis(self):
        self.target_card.diagnosis = "ДЦП"
        self.target_card.save(update_fields=["diagnosis"])
        self._complete_card()
        decision = RefundDecision.objects.get(donor=self.donor)
        self.client.force_authenticate(user=self.donor)

        list_response = self.client.get("/api/refunds/my/")
        option_ids = [item["id"] for item in list_response.data[0]["redirect_options"]]
        self.assertIn(self.target_card.id, option_ids)

        response = self.client.post(
            f"/api/refunds/{decision.id}/choose/",
            {"choice": RefundChoice.REDIRECT, "target_card_id": self.target_card.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.target_card.refresh_from_db()
        self.assertEqual(self.target_card.collected_amount, Decimal("70000.00"))

    def test_no_refund_period_without_leftover(self):
        self.card.collected_amount = Decimal("0.00")
        self.card.save(update_fields=["collected_amount"])
        self._complete_card()

        self.assertEqual(self.card.status, CardStatus.COMPLETED)
        self.assertEqual(RefundDecision.objects.filter(card=self.card).count(), 0)

    def test_maybe_open_refund_period_is_idempotent(self):
        self.card.status = CardStatus.COMPLETED
        self.card.save(update_fields=["status"])
        maybe_open_refund_period(self.card)
        count_after_first = RefundDecision.objects.filter(card=self.card).count()
        maybe_open_refund_period(self.card)
        self.assertEqual(RefundDecision.objects.filter(card=self.card).count(), count_after_first)

    def test_process_refund_deadlines_expires_and_applies_keep(self):
        self._complete_card()
        RefundDecision.objects.filter(card=self.card).update(
            deadline=timezone.now() - timedelta(hours=1)
        )

        expired_count, archived_count = process_expired_refund_deadlines()

        self.assertEqual(expired_count, 2)
        self.assertEqual(archived_count, 1)
        decisions = RefundDecision.objects.filter(card=self.card)
        self.assertTrue(
            all(
                item.status == RefundDecisionStatus.EXPIRED
                and item.choice == RefundChoice.KEEP
                for item in decisions
            )
        )
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.ARCHIVED)
        self.assertEqual(self.card.collected_amount, Decimal("110000.00"))

    def test_card_archived_when_all_decisions_done(self):
        self._complete_card()
        decisions = RefundDecision.objects.filter(card=self.card)
        for decision in decisions:
            decision.deadline = timezone.now() + timedelta(days=1)
            decision.save(update_fields=["deadline"])

        self.client.force_authenticate(user=self.donor)
        donor_decision = decisions.get(donor=self.donor)
        self.client.post(
            f"/api/refunds/{donor_decision.id}/choose/",
            {"choice": RefundChoice.KEEP},
            format="json",
        )
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.REDISTRIBUTION)

        self.client.force_authenticate(user=self.other_donor)
        other_decision = decisions.get(donor=self.other_donor)
        response = self.client.post(
            f"/api/refunds/{other_decision.id}/choose/",
            {"choice": RefundChoice.KEEP},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.ARCHIVED)

    def test_management_command_process_refund_deadlines(self):
        self._complete_card()
        RefundDecision.objects.filter(card=self.card).update(
            deadline=timezone.now() - timedelta(minutes=5)
        )

        call_command("process_refund_deadlines")

        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.ARCHIVED)

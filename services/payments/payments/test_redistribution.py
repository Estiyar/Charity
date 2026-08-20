from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role

from .models import Donation, PaymentStatus, RefundChoice, RefundDecision, RefundDecisionStatus


def deceased_card(**overrides):
    payload = {
        "id": 10,
        "status": "deceased",
        "author_id": 99,
        "full_name": "Завершаемый сбор",
        "diagnosis": "Онкология",
        "city": "Алматы",
        "collected_amount": "110000.00",
        "escrow_balance": "110000.00",
        "target_amount": "500000.00",
    }
    payload.update(overrides)
    return payload


def active_target(**overrides):
    payload = {
        "id": 20,
        "status": "active",
        "author_id": 99,
        "full_name": "Активный сбор",
        "diagnosis": "Онкология",
        "city": "Астана",
        "collected_amount": "10000.00",
        "target_amount": "300000.00",
    }
    payload.update(overrides)
    return payload


class RedistributionAPITestCase(APITestCase):
    def setUp(self):
        self.donor = make_principal(5, Role.DONOR, email="donor@test.com", full_name="Иван Донор")
        self.other = make_principal(6, Role.DONOR, email="other@test.com", full_name="Другой донор")
        cards_services = patch("payments.services.cards_client")
        cards_redist = patch("payments.redistribution.cards_client")
        admin_patch = patch("payments.services.admin_client")
        self.mock_cards = cards_services.start()
        self.mock_redist_cards = cards_redist.start()
        self.mock_admin = admin_patch.start()
        self.addCleanup(cards_services.stop)
        self.addCleanup(cards_redist.stop)
        self.addCleanup(admin_patch.stop)
        self.mock_admin.return_value.get.return_value = {
            "refund_commission_percent": 10,
            "refund_deadline_days": 7,
        }
        self.card = deceased_card()
        self.target = active_target()
        self.mock_cards.return_value.get.side_effect = self._get_card
        self.mock_cards.return_value.post.return_value = self.card
        self.mock_redist_cards.return_value.get.side_effect = self._get_card
        self.mock_redist_cards.return_value.post.return_value = {**self.card, "status": "redistribution"}
        self.donation = Donation.objects.create(
            card_id=self.card["id"],
            card_name=self.card["full_name"],
            donor_id=self.donor.id,
            donor_name=self.donor.full_name,
            amount=Decimal("60000.00"),
            payment_status=PaymentStatus.SUCCESS,
            idempotency_key="d1",
        )
        Donation.objects.create(
            card_id=self.card["id"],
            card_name=self.card["full_name"],
            donor_id=self.other.id,
            donor_name=self.other.full_name,
            amount=Decimal("50000.00"),
            payment_status=PaymentStatus.SUCCESS,
            idempotency_key="d2",
        )

    def _get_card(self, path, **kwargs):
        if path.startswith("/internal/cards/") and path.endswith("/") and path.count("/") == 4:
            card_id = int(path.split("/")[3])
            if card_id == self.target["id"]:
                return self.target
            return self.card
        if path == "/internal/cards/":
            return [self.target]
        return self.card

    def _open_period(self):
        from .redistribution import maybe_open_redistribution_period

        maybe_open_redistribution_period(self.card)

    def test_public_refund_api_is_closed(self):
        self.client.force_authenticate(self.donor)
        for path, method in (
            ("/api/refunds/my/", "get"),
            ("/api/refunds/history/", "get"),
            ("/api/refunds/1/choose/", "post"),
        ):
            response = getattr(self.client, method)(path, {"choice": "refund"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_410_GONE, path)
            self.assertEqual(response.data["code"], "refund_disabled")

    def test_opens_redistribution_without_refund_option(self):
        self._open_period()
        self.client.force_authenticate(self.donor)
        response = self.client.get("/api/redistribution/my/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        values = [item["value"] for item in response.data[0]["options"]]
        self.assertEqual(values, ["keep", "hold", "redirect"])
        self.assertNotIn("refund", values)
        self.assertIsNone(response.data[0]["refund_payout"])

    def test_choose_refund_is_rejected(self):
        self._open_period()
        decision = RefundDecision.objects.get(donor_id=self.donor.id)
        self.client.force_authenticate(self.donor)
        self.mock_redist_cards.return_value.post.reset_mock()
        response = self.client.post(
            f"/api/redistribution/{decision.id}/choose/",
            {"choice": RefundChoice.REFUND},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        decision.refresh_from_db()
        self.assertEqual(decision.status, RefundDecisionStatus.PENDING)
        self.mock_redist_cards.return_value.post.assert_not_called()

    def test_choose_keep_leaves_funds_on_card(self):
        self._open_period()
        decision = RefundDecision.objects.get(donor_id=self.donor.id)
        self.client.force_authenticate(self.donor)
        response = self.client.post(
            f"/api/redistribution/{decision.id}/choose/",
            {"choice": RefundChoice.KEEP},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decision.refresh_from_db()
        self.assertEqual(decision.choice, RefundChoice.KEEP)
        collect_calls = [
            call for call in self.mock_redist_cards.return_value.post.call_args_list
            if "/collect/" in call.args[0]
        ]
        self.assertEqual(collect_calls, [])

    def test_choose_hold_keeps_card_unarchived(self):
        self._open_period()
        for decision in RefundDecision.objects.filter(card_id=self.card["id"]):
            self.client.force_authenticate(
                self.donor if decision.donor_id == self.donor.id else self.other
            )
            response = self.client.post(
                f"/api/redistribution/{decision.id}/choose/",
                {"choice": RefundChoice.HOLD},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        archive_calls = [
            call for call in self.mock_redist_cards.return_value.post.call_args_list
            if "/transition/" in call.args[0] and call.kwargs.get("json", {}).get("status") == "archived"
        ]
        self.assertEqual(archive_calls, [])

    def test_choose_redirect_moves_amount(self):
        self._open_period()
        decision = RefundDecision.objects.get(donor_id=self.donor.id)
        self.client.force_authenticate(self.donor)
        response = self.client.post(
            f"/api/redistribution/{decision.id}/choose/",
            {"choice": RefundChoice.REDIRECT, "target_card_id": self.target["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        paths = [call.args[0] for call in self.mock_redist_cards.return_value.post.call_args_list]
        self.assertTrue(any(f"/internal/cards/{self.card['id']}/collect/" in path for path in paths))
        self.assertTrue(any(f"/internal/cards/{self.target['id']}/collect/" in path for path in paths))

    def test_history_keeps_legacy_refund_records(self):
        RefundDecision.objects.create(
            donation=self.donation,
            card_id=self.card["id"],
            card_snapshot=self.card,
            donor_id=self.donor.id,
            share_amount=Decimal("60000.00"),
            choice=RefundChoice.REFUND,
            status=RefundDecisionStatus.DONE,
            deadline=timezone.now() - timedelta(days=1),
            resolved_at=timezone.now(),
        )
        self.client.force_authenticate(self.donor)
        response = self.client.get("/api/redistribution/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["choice"], RefundChoice.REFUND)
        self.assertIsNotNone(response.data[0]["refund_payout"])

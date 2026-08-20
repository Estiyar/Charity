from datetime import date
from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import CardStatus, RelationshipType, Role
from ekomek_common.risk import RiskLevel

from .business_limits import BusinessLimitViolation, check_fundraiser_creation_frequency
from .models import FundraisingCard
from .risk_engine import calculate_risk_score, override_risk, should_auto_suspend, should_trigger_manual_review
from .risk_models import RiskAssessment, RiskOverride


def _make_card(**overrides):
    defaults = {
        "author_id": 11,
        "author_email": "a@t.com",
        "full_name": "Test",
        "diagnosis": "X",
        "city": "Almaty",
        "target_amount": Decimal("10000"),
        "end_date": date(2027, 1, 1),
        "status": CardStatus.DRAFT,
        "is_self": True,
        "relationship_type": RelationshipType.SELF,
    }
    defaults.update(overrides)
    return FundraisingCard.objects.create(**defaults)


class RiskEngineTest(APITestCase):
    def setUp(self):
        self.moderator = make_principal(31, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.admin_config = patch("cards.risk_engine._fetch_risk_config")
        self.mock_config = self.admin_config.start()
        self.mock_config.return_value = None
        self.addCleanup(self.admin_config.stop)

        self.fraud_patch = patch("cards.risk_engine.verification_client")
        self.mock_fraud = self.fraud_patch.start()
        self.mock_fraud.return_value.get.return_value = None
        self.addCleanup(self.fraud_patch.stop)

    def test_clean_card_has_low_risk(self):
        card = _make_card()
        assessment = calculate_risk_score(card)
        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertEqual(assessment.risk_score, 0)
        self.assertFalse(should_auto_suspend(assessment))

    def test_duplicate_signals_increase_risk(self):
        card = _make_card(
            duplicate_suspected=True,
            duplicate_signals=[
                {"code": "same_beneficiary_iin_hash", "message": "match", "matched_card_ids": [2]},
                {"code": "reused_payout_details", "message": "reused", "matched_card_ids": [3]},
            ],
        )
        assessment = calculate_risk_score(card)
        self.assertGreater(assessment.risk_score, 0)
        codes = [f["code"] for f in assessment.factors]
        self.assertIn("duplicate_beneficiary", codes)
        self.assertIn("reused_payout_details", codes)

    def test_fraud_list_match_triggers_high_risk(self):
        self.mock_fraud.return_value.get.return_value = {
            "risk_score": 80,
            "risk_level": "high",
            "reasons": ["fraud_db_match"],
        }
        card = _make_card(iin_hash="hash-test", report_risk_score=25)
        assessment = calculate_risk_score(card)
        self.assertGreaterEqual(assessment.risk_score, 56)
        self.assertTrue(should_trigger_manual_review(assessment))

    def test_report_risk_contributes_to_score(self):
        card = _make_card(report_risk_score=25)
        assessment = calculate_risk_score(card)
        codes = [f["code"] for f in assessment.factors]
        self.assertIn("substantiated_reports", codes)

    def test_recalculation_idempotent(self):
        card = _make_card()
        first = calculate_risk_score(card)
        second = calculate_risk_score(card)
        self.assertEqual(first.id, second.id)

    def test_recalculation_updates_when_changed(self):
        card = _make_card()
        first = calculate_risk_score(card)
        card.report_risk_score = 30
        card.save(update_fields=["report_risk_score"])
        second = calculate_risk_score(card)
        self.assertNotEqual(first.id, second.id)
        self.assertGreater(second.risk_score, first.risk_score)

    def test_override_creates_record(self):
        card = _make_card()
        calculate_risk_score(card)
        override = override_risk(card.id, self.moderator, 10, "Проверка завершена")
        self.assertEqual(override.new_score, 10)
        self.assertEqual(override.moderator_name, "Модератор")
        latest = RiskAssessment.latest_for_card(card.id)
        self.assertEqual(latest.risk_score, 10)
        self.assertEqual(RiskOverride.objects.filter(card_id=card.id).count(), 1)


class RiskViewsTest(APITestCase):
    def setUp(self):
        self.moderator = make_principal(31, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.author = make_principal(11, Role.AUTHOR, email="a@t.com")
        self.card = _make_card()

        config = patch("cards.risk_engine._fetch_risk_config")
        self.mock_config = config.start()
        self.mock_config.return_value = None
        self.addCleanup(config.stop)

        fraud = patch("cards.risk_engine.verification_client")
        self.mock_fraud = fraud.start()
        self.mock_fraud.return_value.get.return_value = None
        self.addCleanup(fraud.stop)

    def test_risk_assessment_endpoint(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.get(f"/api/cards/{self.card.id}/risk/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("risk_score", response.data)
        self.assertIn("factors", response.data)

    def test_recalculate_endpoint(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.post(f"/api/cards/{self.card.id}/risk/recalculate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_override_endpoint(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.post(
            f"/api/cards/{self.card.id}/risk/override/",
            {"risk_score": 5, "reason": "Ручная проверка"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["new_score"], 5)

    def test_override_requires_reason(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.post(
            f"/api/cards/{self.card.id}/risk/override/",
            {"risk_score": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_author_cannot_access_risk(self):
        self.client.force_authenticate(self.author)
        response = self.client.get(f"/api/cards/{self.card.id}/risk/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_internal_risk_endpoint(self):
        response = self.client.get(
            f"/internal/cards/{self.card.id}/risk/",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BusinessLimitsTest(APITestCase):
    def setUp(self):
        self.limits_patch = patch("cards.business_limits._fetch_limits")
        self.mock_limits = self.limits_patch.start()
        self.mock_limits.return_value = {
            "max_fundraisers_per_author_per_month": 2,
            "max_fundraisers_per_author_total_active": 1,
            "beneficiary_change_after_activation_forbidden": True,
        }
        self.addCleanup(self.limits_patch.stop)

    def test_frequency_limit_blocks_third_fundraiser(self):
        _make_card(author_id=99)
        _make_card(author_id=99)
        with self.assertRaises(BusinessLimitViolation):
            check_fundraiser_creation_frequency(99)

    def test_frequency_limit_allows_first(self):
        check_fundraiser_creation_frequency(88)

    def test_active_limit_blocks_second_active(self):
        _make_card(author_id=77, status=CardStatus.ACTIVE)
        with self.assertRaises(BusinessLimitViolation):
            check_fundraiser_creation_frequency(77)

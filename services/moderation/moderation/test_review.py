from unittest.mock import patch

from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import CardStatus, Role, UserStatus
from ekomek_common.outbox_app.models import OutboxEvent

from .events import handle_card_manual_review_required, handle_user_manual_review_required
from .models import ManualReviewCase, ReviewDecision
from .review_cases import open_card_review, open_user_review


RAW_IIN = "990101300999"


class FakeClient:
    def __init__(self):
        self.user = {
            "id": 5,
            "full_name": "Риск Автор",
            "email": "risk@test.com",
            "role": Role.AUTHOR,
            "status": UserStatus.MANUAL_REVIEW,
            "iin_hash": "hash-user",
            "iin_masked": "9901*****999",
            "ecp_verification_id": 7,
        }
        self.card = {
            "id": 9,
            "full_name": "Риск Карточка",
            "status": CardStatus.MANUAL_REVIEW,
            "high_risk": True,
            "needs_extra_review": True,
            "review_reasons": ["high_risk_iin"],
            "iin_hash": "hash-card",
            "iin_masked": "9901*****999",
        }
        self.posts = []

    def get(self, path, **kwargs):
        if path.startswith("/internal/users/"):
            return dict(self.user)
        if "/documents/" in path:
            return [
                {
                    "id": 3,
                    "card_id": 9,
                    "file_url": "/secret.pdf",
                    "file_name": "scan.pdf",
                    "file_type": "medical",
                    "status": "pending",
                    "has_confidential": True,
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ]
        if path.startswith("/internal/cards/"):
            return dict(self.card)
        if "antifraud/hash" in path:
            return {
                "iin": RAW_IIN,
                "iin_masked": "9901*****999",
                "risk_score": 92,
                "risk_level": "high",
                "reasons": ["fraud_list", "duplicate_card"],
            }
        if "medregistry/hash" in path:
            return {"iin": RAW_IIN, "diagnosis": "Онкология", "iin_masked": "9901*****999"}
        if "ecp/verifications" in path:
            return {"verification_id": 7, "certificate_type": "NCALayer", "iin": RAW_IIN}
        return {}

    def post(self, path, json=None, **kwargs):
        self.posts.append((path, json or {}))
        if "set-status" in path:
            self.user["status"] = json["status"]
            return dict(self.user)
        if "transition" in path:
            self.card["status"] = json["status"]
            return dict(self.card)
        return {}


class ManualReviewQueueTest(APITestCase):
    def setUp(self):
        self.fake = FakeClient()
        self.moderator = make_principal(10, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.admin = make_principal(11, Role.ADMIN, email="admin@test.com", full_name="Админ")
        self.donor = make_principal(12, Role.DONOR, email="donor@test.com")
        patchers = [
            patch("moderation.review_snapshots.identity_client", return_value=self.fake),
            patch("moderation.review_snapshots.cards_client", return_value=self.fake),
            patch("moderation.review_snapshots.verification_client", return_value=self.fake),
            patch("moderation.review_snapshots.documents_client", return_value=self.fake),
            patch("moderation.review_actions.identity_client", return_value=self.fake),
            patch("moderation.services.cards_client", return_value=self.fake),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_roles(self):
        self.client.force_authenticate(self.donor)
        self.assertEqual(self.client.get("/api/moderation/reviews/").status_code, 403)
        self.client.force_authenticate(self.moderator)
        self.assertEqual(self.client.get("/api/moderation/reviews/").status_code, 200)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/moderation/reviews/").status_code, 200)

    def test_open_user_and_card_cases_are_idempotent(self):
        first = open_user_review({"user_id": 5, "status": UserStatus.MANUAL_REVIEW})
        second = open_user_review({"user_id": 5, "status": UserStatus.MANUAL_REVIEW})
        self.assertEqual(first.id, second.id)
        self.assertEqual(ManualReviewCase.objects.filter(subject_type="user", subject_id=5).count(), 1)
        card_first = open_card_review({"card_id": 9, "status": CardStatus.MANUAL_REVIEW, "high_risk": True})
        card_second = open_card_review({"card_id": 9, "status": CardStatus.MANUAL_REVIEW, "high_risk": True})
        self.assertEqual(card_first.id, card_second.id)

    def test_draft_high_risk_card_is_not_queued(self):
        self.fake.card["status"] = CardStatus.DRAFT
        handle_card_manual_review_required({"card_id": 9, "reasons": ["high_risk_iin"]})
        self.assertFalse(ManualReviewCase.objects.filter(subject_type="card").exists())

    def test_queue_and_snapshot_hide_raw_iin(self):
        handle_user_manual_review_required({"user_id": 5, "status": UserStatus.MANUAL_REVIEW})
        self.client.force_authenticate(self.moderator)
        listed = self.client.get("/api/moderation/reviews/")
        self.assertEqual(len(listed.data), 1)
        detail = self.client.get(f"/api/moderation/reviews/{listed.data[0]['id']}/")
        body = str(detail.data)
        self.assertNotIn(RAW_IIN, body)
        self.assertEqual(detail.data["risk_score"], 92)
        self.assertEqual(detail.data["risk_level"], "high")
        self.assertIn("fraud_list", detail.data["risk_reasons"])
        self.assertIn("duplicate_card", detail.data["duplicate_signals"])
        self.assertEqual(detail.data["verification_snapshot"]["ecp"]["certificate_type"], "NCALayer")

    def test_approve_user_and_card(self):
        user_case = open_user_review({"user_id": 5, "status": UserStatus.MANUAL_REVIEW})
        card_case = open_card_review({"card_id": 9, "status": CardStatus.MANUAL_REVIEW, "high_risk": True})
        self.client.force_authenticate(self.moderator)
        card_detail = self.client.get(f"/api/moderation/reviews/{card_case.id}/")
        self.assertEqual(card_detail.data["document_metadata"][0]["file_name"], "scan.pdf")
        self.assertNotIn("file_url", card_detail.data["document_metadata"][0])
        self.assertNotIn(RAW_IIN, str(card_detail.data))
        user_response = self.client.post(
            f"/api/moderation/reviews/{user_case.id}/approve/",
            {"comment": "ok", "idempotency_key": "user-approve-1"},
            format="json",
        )
        self.assertEqual(user_response.status_code, 200, user_response.data)
        self.assertEqual(self.fake.user["status"], UserStatus.ECP_VERIFIED)
        card_response = self.client.post(
            f"/api/moderation/reviews/{card_case.id}/approve/",
            {"idempotency_key": "card-approve-1"},
            format="json",
        )
        self.assertEqual(card_response.status_code, 200, card_response.data)
        self.assertEqual(self.fake.card["status"], CardStatus.ACTIVE)
        self.assertTrue(OutboxEvent.objects.filter(event_type="review.decision_applied").exists())
        self.assertEqual(self.fake.posts[-1][1].get("duplicate_override"), True)

    def test_card_snapshot_keeps_explainable_duplicate_matches(self):
        self.fake.card["duplicate_signals"] = [
            {
                "code": "same_beneficiary_iin_hash",
                "message": "Совпадает получатель с карточкой #4.",
                "matched_card_ids": [4],
            }
        ]
        self.fake.card["duplicate_matches"] = [
            {
                "card_id": 4,
                "status": CardStatus.COMPLETED,
                "iin_masked": "8503*****234",
                "signal_codes": ["same_beneficiary_iin_hash"],
            }
        ]
        self.fake.card["duplicate_risk_delta"] = 15
        case = open_card_review({"card_id": 9, "status": CardStatus.MANUAL_REVIEW, "high_risk": True})
        self.client.force_authenticate(self.moderator)
        detail = self.client.get(f"/api/moderation/reviews/{case.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn(RAW_IIN, str(detail.data))
        self.assertEqual(detail.data["duplicate_signals"][0]["code"], "same_beneficiary_iin_hash")
        self.assertEqual(detail.data["risk_score"], 100)
        self.assertEqual(detail.data["evidence_snapshot"]["duplicate_matches"][0]["card_id"], 4)

    def test_reject_and_revision_require_comment(self):
        case = open_user_review({"user_id": 5, "status": UserStatus.MANUAL_REVIEW})
        self.client.force_authenticate(self.moderator)
        reject = self.client.post(f"/api/moderation/reviews/{case.id}/reject/", {}, format="json")
        self.assertEqual(reject.status_code, 400)
        revision = self.client.post(
            f"/api/moderation/reviews/{case.id}/request-revision/",
            {"comment": "Нужны документы"},
            format="json",
        )
        self.assertEqual(revision.status_code, 200, revision.data)
        case.refresh_from_db()
        self.assertEqual(case.status, ManualReviewCase.Status.REVISION_REQUIRED)
        self.assertEqual(self.fake.user["status"], UserStatus.MANUAL_REVIEW)

    def test_suspend_unsuspend_and_idempotent_repeat(self):
        case = open_card_review({"card_id": 9, "status": CardStatus.MANUAL_REVIEW, "high_risk": True})
        self.client.force_authenticate(self.moderator)
        first = self.client.post(
            f"/api/moderation/reviews/{case.id}/suspend/",
            {"idempotency_key": "suspend-1"},
            format="json",
        )
        second = self.client.post(
            f"/api/moderation/reviews/{case.id}/suspend/",
            {"idempotency_key": "suspend-1"},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ReviewDecision.objects.filter(case=case, action="suspend").count(), 1)
        self.assertEqual(self.fake.card["status"], CardStatus.SUSPENDED)
        unsuspend = self.client.post(f"/api/moderation/reviews/{case.id}/unsuspend/", {}, format="json")
        self.assertEqual(unsuspend.status_code, 200, unsuspend.data)
        self.assertEqual(self.fake.card["status"], CardStatus.MANUAL_REVIEW)

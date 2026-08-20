from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import CardStatus, RelationshipType, Role
from ekomek_common.crypto import hmac_hash

from .events import on_document_expired, on_document_uploaded
from .history_services import apply_card_field_updates
from .models import CardHistoryEvent, FundraisingCard
from .trust_services import build_trust_status

RECIPIENT_IIN = "850315301234"


def make_card(**overrides):
    payload = {
        "author_id": 11,
        "author_email": "author@test.com",
        "full_name": "Получатель",
        "diagnosis": "Онкология",
        "description": "Нужна операция",
        "city": "Almaty",
        "clinic": "Клиника №1",
        "target_amount": Decimal("1000"),
        "end_date": date(2027, 1, 1),
        "status": CardStatus.ACTIVE,
        "is_self": True,
        "relationship_type": RelationshipType.SELF,
        "moderation_verified_at": timezone.now(),
    }
    payload.update(overrides)
    card = FundraisingCard.objects.create(**payload)
    card.assign_iin(RECIPIENT_IIN)
    card.save(update_fields=["iin_hash", "iin_masked", "iin_encrypted"])
    return card


class TrustAndHistoryTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com")
        self.identity = patch("cards.trust_services.identity_client").start()
        self.profile = patch("cards.trust_services.profile_client").start()
        self.documents = patch("cards.trust_services.documents_client").start()
        self.expenses = patch("cards.trust_services.expenses_client").start()
        self.addCleanup(patch.stopall)
        self.identity.return_value.get.return_value = {}
        self.profile.return_value.get.return_value = {}
        self.documents.return_value.get.return_value = []
        self.expenses.return_value.get.return_value = {"approved_count": 0}

    def test_unverified_badges_are_not_marked_success(self):
        card = make_card(moderation_verified_at=None, status=CardStatus.DRAFT)
        payload = build_trust_status(card)
        self.assertIsNone(payload["last_verified_at"])
        for badge in payload["badges"]:
            self.assertFalse(badge["verified"])
            self.assertIsNone(badge["verified_at"])
        public = self.client.get(f"/api/cards/{card.id}/trust-status/")
        self.assertEqual(public.status_code, status.HTTP_404_NOT_FOUND)

    def test_completed_verifications_produce_badges(self):
        card = make_card(
            status=CardStatus.ACTIVE,
            beneficiary_id=7,
            representation_id=9,
            is_self=False,
            relationship_type=RelationshipType.REPRESENTATIVE,
            medical_source="official",
        )
        card.diagnosis_verified_at = card.created_at
        card.clinic_verified_at = card.created_at
        card.moderation_verified_at = card.created_at
        card.save()
        self.identity.return_value.get.return_value = {
            "ecp_verification_id": 4,
            "created_at": "2026-01-01T00:00:00Z",
        }
        self.profile.return_value.get.side_effect = [
            {"verification_status": "verified", "verified_at": "2026-01-02T00:00:00Z"},
            {"verification_status": "verified", "verified_at": "2026-01-03T00:00:00Z"},
        ]
        self.documents.return_value.get.return_value = [
            {"status": "verified", "updated_at": "2026-01-04T00:00:00Z"}
        ]
        self.expenses.return_value.get.return_value = {
            "approved_count": 1,
            "last_approved_at": "2026-01-05T00:00:00Z",
        }
        payload = self.client.get(f"/api/cards/{card.id}/trust-status/").data
        verified = {item["code"]: item for item in payload["badges"] if item["verified"]}
        self.assertEqual(
            set(verified),
            {
                "author_eds_verified",
                "beneficiary_verified",
                "representation_verified",
                "documents_verified",
                "diagnosis_verified",
                "clinic_verified",
                "moderator_approved",
                "expenses_verified",
            },
        )
        self.assertTrue(payload["last_verified_at"])
        self.assertNotIn(RECIPIENT_IIN, str(payload))

    def test_dev_medical_source_does_not_verify_diagnosis(self):
        card = make_card(medical_source="dev", diagnosis_verified_at=None, clinic_verified_at=None)
        payload = build_trust_status(card)
        codes = {item["code"]: item["verified"] for item in payload["badges"]}
        self.assertFalse(codes["diagnosis_verified"])
        self.assertFalse(codes["clinic_verified"])

    def test_history_is_immutable_and_permission_safe(self):
        card = make_card(status=CardStatus.DRAFT, moderation_verified_at=None)
        apply_card_field_updates(card, {"target_amount": Decimal("2500")}, actor=self.author)
        apply_card_field_updates(card, {"payout_details_hash": hmac_hash("iban")}, actor=self.author)
        event = CardHistoryEvent.objects.filter(event_type="target_amount_changed").first()
        with self.assertRaises(ValueError):
            event.summary = "hack"
            event.save()
        with self.assertRaises(ValueError):
            event.delete()
        self.client.force_authenticate(self.author)
        public = self.client.get(f"/api/cards/{card.id}/history/")
        types = [item["event_type"] for item in public.data]
        self.assertIn("target_amount_changed", types)
        self.assertNotIn("payout_details_changed", types)
        self.assertNotIn("actor_id", public.data[0])
        self.assertNotIn(RECIPIENT_IIN, str(public.data))
        self.client.force_authenticate(self.moderator)
        staff = self.client.get(f"/api/cards/{card.id}/history/")
        staff_types = [item["event_type"] for item in staff.data]
        self.assertIn("payout_details_changed", staff_types)
        payout = next(item for item in staff.data if item["event_type"] == "payout_details_changed")
        self.assertNotIn(hmac_hash("iban"), str(payout["payload"]))

    def test_critical_change_after_activation_requires_remoderation(self):
        card = make_card(status=CardStatus.ACTIVE)
        self.client.force_authenticate(self.author)
        response = self.client.patch(
            f"/api/cards/{card.id}/",
            {"diagnosis": "Кардиология", "description": "Новая цель лечения"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.MANUAL_REVIEW)
        self.assertIsNone(card.diagnosis_verified_at)
        self.assertIsNone(card.moderation_verified_at)
        catalog = self.client.get("/api/catalog/")
        self.assertNotIn(card.id, [item["id"] for item in catalog.data["results"]])
        trust = build_trust_status(card)
        moderator = next(item for item in trust["badges"] if item["code"] == "moderator_approved")
        self.assertFalse(moderator["verified"])

    def test_document_upload_on_active_card_is_logged_and_remoderated(self):
        card = make_card(status=CardStatus.ACTIVE)
        on_document_uploaded({"card_id": card.id, "document_id": 3, "replaced": False})
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.MANUAL_REVIEW)
        self.assertTrue(card.history_events.filter(event_type="document_added", public=True).exists())
        detail = self.client.get(f"/api/cards/{card.id}/")
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_expired_document_requires_revision(self):
        card = make_card(status=CardStatus.ACTIVE)
        on_document_expired({"card_id": card.id, "document_id": 4})
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.REVISION_REQUIRED)
        self.assertIsNone(card.moderation_verified_at)

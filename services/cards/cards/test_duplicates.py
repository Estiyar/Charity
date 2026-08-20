from datetime import date
from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import CardStatus, RelationshipType, Role
from ekomek_common.crypto import hmac_hash
from ekomek_common.masking import mask_iin
from ekomek_common.outbox_app.models import OutboxEvent

from .duplicate_services import apply_duplicate_check
from .models import DuplicateCheck, FundraisingCard

RECIPIENT_IIN = "850315301234"
OTHER_IIN = "900101300111"
LONG_PURPOSE = "Нужна операция и длительная реабилитация в клинике после лечения."


def make_card(**overrides):
    iin = overrides.pop("iin", RECIPIENT_IIN)
    document_number = overrides.pop("document_number", None)
    payload = {
        "author_id": 11,
        "author_email": "author@test.com",
        "full_name": "Получатель",
        "diagnosis": "Онкология",
        "description": LONG_PURPOSE,
        "city": "Almaty",
        "target_amount": Decimal("1000"),
        "end_date": date(2027, 1, 1),
        "status": CardStatus.DRAFT,
        "is_self": True,
        "relationship_type": RelationshipType.SELF,
        "iin_masked": mask_iin(iin) if iin else "",
    }
    payload.update(overrides)
    card = FundraisingCard.objects.create(**payload)
    if iin:
        card.assign_iin(iin)
    if document_number:
        card.assign_document_number(document_number)
    card.save()
    return card


def signal_codes(card):
    return [item["code"] for item in card.duplicate_signals]


class DuplicateDetectionTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        docs = patch("cards.duplicate_services.documents_client")
        self.docs = docs.start()
        self.addCleanup(docs.stop)
        self.docs.return_value.get.return_value = []

    def catalog_ids(self):
        return [item["id"] for item in self.client.get("/api/catalog/").data["results"]]

    def test_true_duplicate_goes_to_manual_review(self):
        original = make_card(status=CardStatus.COMPLETED, full_name="История")
        draft = make_card(full_name="Новый сбор")
        self.client.force_authenticate(self.author)
        response = self.client.post(f"/api/cards/{draft.id}/submit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        draft.refresh_from_db()
        original.refresh_from_db()
        self.assertEqual(original.status, CardStatus.COMPLETED)
        self.assertTrue(draft.duplicate_suspected)
        self.assertEqual(draft.status, CardStatus.MANUAL_REVIEW)
        self.assertIn("same_beneficiary_iin_hash", signal_codes(draft))
        self.assertIn("similar_diagnosis_purpose", signal_codes(draft))
        self.assertGreater(draft.duplicate_risk_delta, 0)
        self.assertNotIn(draft.id, self.catalog_ids())
        self.assertNotIn(RECIPIENT_IIN, str(response.data))
        event = OutboxEvent.objects.get(event_type="card.duplicate_detected")
        self.assertNotIn(RECIPIENT_IIN, str(event.payload))
        self.assertEqual(event.payload["matched_card_ids"], [original.id])
        internal = self.client.get(
            f"/internal/cards/{draft.id}/",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertNotIn(RECIPIENT_IIN, str(internal.data))
        for match in internal.data["duplicate_matches"]:
            self.assertNotIn("iin_hash", match)
            self.assertNotIn(RECIPIENT_IIN, str(match))

    def test_non_duplicate_can_be_published(self):
        card = make_card(iin=OTHER_IIN, diagnosis="Кардиология", description="Другая цель лечения сердца и реабилитации.")
        self.client.force_authenticate(self.author)
        submitted = self.client.post(f"/api/cards/{card.id}/submit/")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK, submitted.data)
        card.refresh_from_db()
        self.assertFalse(card.duplicate_suspected)
        self.assertEqual(card.status, CardStatus.PENDING_MODERATION)
        activated = self.client.post(
            f"/internal/cards/{card.id}/transition/",
            {"status": CardStatus.ACTIVE},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(activated.status_code, status.HTTP_200_OK, activated.data)
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.ACTIVE)
        self.assertIn(card.id, self.catalog_ids())

    def test_false_positive_requires_manual_override(self):
        make_card(status=CardStatus.COMPLETED, iin=RECIPIENT_IIN)
        draft = make_card(iin=OTHER_IIN)
        self.client.force_authenticate(self.author)
        self.client.post(f"/api/cards/{draft.id}/submit/")
        draft.refresh_from_db()
        self.assertTrue(draft.duplicate_suspected)
        self.assertIn("similar_diagnosis_purpose", signal_codes(draft))
        blocked = self.client.post(
            f"/internal/cards/{draft.id}/transition/",
            {"status": CardStatus.ACTIVE},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        draft.refresh_from_db()
        self.assertEqual(draft.status, CardStatus.MANUAL_REVIEW)
        self.assertNotIn(draft.id, self.catalog_ids())
        allowed = self.client.post(
            f"/internal/cards/{draft.id}/transition/",
            {"status": CardStatus.ACTIVE, "duplicate_override": True},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)
        draft.refresh_from_db()
        self.assertTrue(draft.duplicate_suspected)
        self.assertTrue(draft.duplicate_override)
        self.assertEqual(draft.status, CardStatus.ACTIVE)
        self.assertIn(draft.id, self.catalog_ids())

    def test_duplicate_check_is_idempotent(self):
        make_card(status=CardStatus.COMPLETED)
        draft = make_card()
        first = apply_duplicate_check(draft)
        risk = draft.duplicate_risk_delta
        second = apply_duplicate_check(draft)
        draft.refresh_from_db()
        self.assertEqual(first.id, second.id)
        self.assertEqual(DuplicateCheck.objects.filter(card=draft).count(), 1)
        self.assertEqual(draft.duplicate_risk_delta, risk)
        self.assertEqual(OutboxEvent.objects.filter(event_type="card.duplicate_detected").count(), 1)

    def test_document_number_and_payout_hashes_are_explainable(self):
        make_card(
            status=CardStatus.COMPLETED,
            iin=RECIPIENT_IIN,
            diagnosis="Травма",
            description="Совсем другая цель лечения после травмы в клинике.",
            document_number="12345678",
            payout_details_hash=hmac_hash("iban-1"),
        )
        draft = make_card(
            iin=OTHER_IIN,
            diagnosis="Кардиология",
            description="Лечение сердца без пересечения с предыдущей целью.",
            document_number="12345678",
            payout_details_hash=hmac_hash("iban-1"),
        )
        apply_duplicate_check(draft)
        self.assertTrue(draft.duplicate_suspected)
        self.assertIn("duplicate_document_number", signal_codes(draft))
        self.assertIn("reused_payout_details", signal_codes(draft))

    def test_duplicate_document_file_signal(self):
        other = make_card(status=CardStatus.COMPLETED, iin=OTHER_IIN, diagnosis="Травма")
        draft = make_card()
        self.docs.return_value.get.return_value = [
            {"document_id": 4, "card_id": other.id, "file_hash": "abc123"}
        ]
        apply_duplicate_check(draft)
        self.assertIn("duplicate_document_file", signal_codes(draft))
        self.assertTrue(draft.duplicate_suspected)

    def test_author_volume_is_additional_risk_not_silent_reject(self):
        for index in range(3):
            make_card(
                status=CardStatus.COMPLETED,
                iin=f"85031530120{index}",
                diagnosis=f"Unique{index}",
                description=f"Completely different purpose statement number {index} for rehab.",
            )
        draft = make_card(
            iin=OTHER_IIN,
            diagnosis="Кардиология",
            description="Другая цель лечения сердца и реабилитации пациента.",
        )
        self.client.force_authenticate(self.author)
        response = self.client.post(f"/api/cards/{draft.id}/submit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        draft.refresh_from_db()
        self.assertFalse(draft.duplicate_suspected)
        self.assertIn("high_volume_author", signal_codes(draft))
        self.assertTrue(draft.needs_extra_review)
        self.assertEqual(draft.status, CardStatus.MANUAL_REVIEW)
        self.assertEqual(FundraisingCard.objects.count(), 4)

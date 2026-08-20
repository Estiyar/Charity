from datetime import date
from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.audit_app.models import SensitiveAccessLog
from ekomek_common.auth import make_principal
from ekomek_common.constants import Role, CardStatus, RelationshipType, RepresentationStatus, UserStatus
from ekomek_common.crypto import hmac_hash
from ekomek_common.masking import mask_iin

from .models import FundraisingCard

AUTHOR_IIN = "880420301999"
RECIPIENT_IIN = "850315301234"


def medical_snapshot(iin=RECIPIENT_IIN, **overrides):
    payload = {
        "iin": iin,
        "iin_hash": hmac_hash(iin),
        "iin_masked": mask_iin(iin),
        "full_name": "Айгуль Смагулова",
        "birth_date": "1985-03-15",
        "city": "Алматы",
        "clinic": "Городская поликлиника №5",
        "diagnosis": "Онкология",
        "gender": "female",
        "age": 41,
        "source": "dev",
        "found": True,
        "unavailable": False,
        "incomplete": False,
        "inconsistent": False,
        "blocked": False,
        "high_risk": False,
        "requires_manual_review": False,
        "review_reasons": [],
        "is_self": iin == AUTHOR_IIN,
    }
    payload.update(overrides)
    return payload


def mock_recipient_clients(identity, verification, profile, *, iin=RECIPIENT_IIN, relationship=RelationshipType.SELF):
    identity.return_value.get.return_value = {
        "iin": AUTHOR_IIN,
        "full_name": "Автор",
        "birth_date": "1988-04-20",
        "iin_hash": hmac_hash(AUTHOR_IIN),
    }

    def verification_post(path, json=None, **kwargs):
        if "recipient/verify" in path:
            used_iin = (json or {}).get("iin") or iin
            return medical_snapshot(used_iin, is_self=used_iin == AUTHOR_IIN)
        if "antifraud" in path:
            return {"blocked": False, "needs_review": False}
        return {"iin": iin, "full_name": "Айгуль Смагулова"}

    verification.return_value.post.side_effect = verification_post
    verification.return_value.get.return_value = {"blocked": False, "needs_review": False}
    profile.return_value.post.return_value = {
        "id": 7,
        "verification_status": "verified",
        "iin": iin,
        "representation": {
            "id": 9,
            "verification_status": (
                RepresentationStatus.VERIFIED
                if relationship == RelationshipType.SELF
                else RepresentationStatus.PENDING
            ),
            "relationship_type": relationship,
        },
    }
    profile.return_value.get.return_value = {
        "id": 9,
        "verification_status": (
            RepresentationStatus.VERIFIED if relationship == RelationshipType.SELF else RepresentationStatus.PENDING
        ),
    }


class CardsAPITestCase(APITestCase):
    def setUp(self):
        self.author = make_principal(
            11, Role.AUTHOR, email="author@test.com", iin=AUTHOR_IIN, full_name="Автор"
        )
        docs = patch("cards.duplicate_services.documents_client")
        self.documents_client = docs.start()
        self.addCleanup(docs.stop)
        self.documents_client.return_value.get.return_value = []
        for target in (
            "cards.trust_services.identity_client",
            "cards.trust_services.profile_client",
            "cards.trust_services.documents_client",
            "cards.trust_services.expenses_client",
        ):
            mocked = patch(target)
            client = mocked.start()
            self.addCleanup(mocked.stop)
            client.return_value.get.return_value = {}

    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)

    def test_public_catalog_empty(self):
        response = self.client.get("/api/cards/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("cards.recipient_services.profile_client")
    @patch("cards.recipient_services.verification_client")
    @patch("cards.recipient_services.identity_client")
    @patch("cards.services.verification_client")
    def test_author_creates_self_card(self, fraud_client, identity, verification, profile):
        mock_recipient_clients(identity, verification, profile, iin=AUTHOR_IIN)
        fraud_client.return_value.get.return_value = {"blocked": False}
        fraud_client.return_value.post.return_value = {"blocked": False}
        self.client.force_authenticate(self.author)
        verified = self.client.post("/api/cards/recipient/verify", {"kind": "self"}, format="json")
        self.assertEqual(verified.status_code, status.HTTP_200_OK, verified.data)
        self.assertEqual(verified.data["full_name"], "Айгуль Смагулова")
        self.assertTrue(verified.data["is_self"])
        self.assertNotIn(AUTHOR_IIN, str(verified.data))
        response = self.client.post(
            "/api/cards/",
            {
                "recipient_session_token": verified.data["recipient_session_token"],
                "target_amount": "100000.00",
                "end_date": "2027-01-01",
                "description": "Help",
                "personal_data_consent": True,
                "document_number": "12345678",
                "contact_phone": "+7 777 123 45 67",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["full_name"], "Айгуль Смагулова")
        self.assertEqual(response.data["iin_masked"], mask_iin(AUTHOR_IIN))
        self.assertNotIn("recipient_iin", response.data)
        self.assertNotIn(AUTHOR_IIN, str(response.data))
        card = FundraisingCard.objects.get()
        self.assertEqual(card.iin_hash, hmac_hash(AUTHOR_IIN))
        self.assertEqual(card.beneficiary_id, 7)
        self.assertTrue(card.is_self)

    @patch("cards.recipient_services.profile_client")
    @patch("cards.recipient_services.verification_client")
    @patch("cards.recipient_services.identity_client")
    @patch("cards.services.verification_client")
    @patch("cards.services.profile_client")
    def test_child_card_cannot_become_active_without_representation(
        self, cards_profile, fraud_client, identity, verification, profile
    ):
        mock_recipient_clients(identity, verification, profile, iin=RECIPIENT_IIN, relationship=RelationshipType.PARENT)
        fraud_client.return_value.get.return_value = {"blocked": False}
        fraud_client.return_value.post.return_value = {"blocked": False}
        cards_profile.return_value.get.return_value = {"verification_status": RepresentationStatus.PENDING}
        self.client.force_authenticate(self.author)
        verified = self.client.post(
            "/api/cards/recipient/verify",
            {"kind": "child", "source_iin": RECIPIENT_IIN, "relationship_type": RelationshipType.PARENT},
            format="json",
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK, verified.data)
        self.assertFalse(verified.data["is_self"])
        self.assertEqual(verified.data["representation_status"], RepresentationStatus.PENDING)
        created = self.client.post(
            "/api/cards/",
            {
                "recipient_session_token": verified.data["recipient_session_token"],
                "target_amount": "100000.00",
                "end_date": "2027-01-01",
                "description": "Help child",
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        card = FundraisingCard.objects.get()
        self.client.post(f"/api/cards/{card.id}/submit/")
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.PENDING_MODERATION)
        response = self.client.post(
            f"/internal/cards/{card.id}/transition/",
            {"status": CardStatus.ACTIVE},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_detail_does_not_expose_full_iin(self):
        card = FundraisingCard(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="Test",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("1000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.ACTIVE,
        )
        card.assign_iin(RECIPIENT_IIN)
        card.assign_document_number("12345678")
        card.assign_contact_phone("+7 777 123 45 67")
        card.save()
        response = self.client.get(f"/api/cards/{card.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["iin_masked"], mask_iin(RECIPIENT_IIN))
        self.assertNotIn(RECIPIENT_IIN, str(response.data))
        self.assertNotIn("12345678", str(response.data))

    def test_staff_detail_reveals_and_audits(self):
        card = FundraisingCard(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="Test",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("1000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.PENDING_MODERATION,
        )
        card.assign_iin(RECIPIENT_IIN)
        card.assign_document_number("12345678")
        card.assign_contact_phone("+7 777 123 45 67")
        card.save()
        moderator = make_principal(22, Role.MODERATOR, email="mod@test.com")
        self.client.force_authenticate(moderator)
        response = self.client.get(f"/api/cards/{card.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["iin"], RECIPIENT_IIN)
        logs = SensitiveAccessLog.objects.filter(resource_id=str(card.id), field_name="iin")
        self.assertTrue(logs.exists())
        self.assertNotIn(RECIPIENT_IIN, str(logs.first().__dict__))

    def test_submit_draft(self):
        card = FundraisingCard.objects.create(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="Test",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("1000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.DRAFT,
            is_self=True,
            relationship_type=RelationshipType.SELF,
        )
        self.client.force_authenticate(self.author)
        response = self.client.post(f"/api/cards/{card.id}/submit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.PENDING_MODERATION)

    def test_high_risk_submit_goes_to_manual_review(self):
        card = FundraisingCard.objects.create(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="High risk",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("1000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.DRAFT,
            high_risk=True,
            needs_extra_review=True,
            is_self=True,
            relationship_type=RelationshipType.SELF,
        )
        self.client.force_authenticate(self.author)
        response = self.client.post(f"/api/cards/{card.id}/submit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.MANUAL_REVIEW)

    def test_manual_review_card_can_be_activated_internally(self):
        card = FundraisingCard.objects.create(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="High risk",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("1000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.MANUAL_REVIEW,
            high_risk=True,
            is_self=True,
            relationship_type=RelationshipType.SELF,
        )
        response = self.client.post(
            f"/internal/cards/{card.id}/transition/",
            {"status": CardStatus.ACTIVE},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.ACTIVE)

    @patch("cards.recipient_services.profile_client")
    @patch("cards.recipient_services.verification_client")
    @patch("cards.recipient_services.identity_client")
    @patch("cards.services.verification_client")
    @patch("cards.services.profile_client")
    def test_other_person_ecp_can_become_active(
        self, cards_profile, fraud_client, identity, verification, profile
    ):
        mock_recipient_clients(
            identity, verification, profile, iin=RECIPIENT_IIN, relationship=RelationshipType.REPRESENTATIVE
        )
        profile.return_value.post.return_value["representation"]["verification_status"] = RepresentationStatus.VERIFIED
        identity.return_value.post.return_value = {"challenge": "abc"}
        fraud_client.return_value.get.return_value = {"blocked": False}
        fraud_client.return_value.post.return_value = {"blocked": False}
        cards_profile.return_value.get.return_value = {"verification_status": RepresentationStatus.VERIFIED}
        self.client.force_authenticate(self.author)
        verified = self.client.post(
            "/api/cards/recipient/verify",
            {"kind": "other", "challenge_id": "ch-1", "cms": "dGVzdA=="},
            format="json",
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK, verified.data)
        self.assertEqual(verified.data["representation_status"], RepresentationStatus.VERIFIED)
        created = self.client.post(
            "/api/cards/",
            {
                "recipient_session_token": verified.data["recipient_session_token"],
                "target_amount": "100000.00",
                "end_date": "2027-01-01",
                "description": "Help other",
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        card = FundraisingCard.objects.get()
        self.client.post(f"/api/cards/{card.id}/submit/")
        response = self.client.post(
            f"/internal/cards/{card.id}/transition/",
            {"status": CardStatus.ACTIVE},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @patch("cards.recipient_services.profile_client")
    def test_existing_beneficiary_can_be_reused(self, profile):
        profile.return_value.get.return_value = {
            "id": 7,
            "owner_user_id": self.author.id,
            "iin": RECIPIENT_IIN,
            "iin_hash": hmac_hash(RECIPIENT_IIN),
            "iin_masked": mask_iin(RECIPIENT_IIN),
            "full_name": "Айгуль Смагулова",
            "medical_linked": True,
            "representation": {
                "id": 9,
                "verification_status": RepresentationStatus.VERIFIED,
                "relationship_type": RelationshipType.SELF,
            },
        }
        self.client.force_authenticate(self.author)
        verified = self.client.post("/api/cards/recipient/verify", {"beneficiary_id": 7}, format="json")
        self.assertEqual(verified.status_code, status.HTTP_200_OK, verified.data)
        self.assertEqual(verified.data["beneficiary_id"], 7)
        self.assertNotIn(RECIPIENT_IIN, str(verified.data))

    def test_beneficiary_can_have_historical_and_new_cards(self):
        completed = FundraisingCard.objects.create(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="История",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("1000"),
            end_date=date(2026, 1, 1),
            status=CardStatus.COMPLETED,
            beneficiary_id=7,
            is_self=True,
            relationship_type=RelationshipType.SELF,
        )
        completed.iin_hash = hmac_hash(RECIPIENT_IIN)
        completed.save(update_fields=["iin_hash"])
        from .repositories import CardRepository

        self.assertFalse(CardRepository().recipient_has_active(hmac_hash(RECIPIENT_IIN)))
        FundraisingCard.objects.create(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="Новый сбор",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("2000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.DRAFT,
            beneficiary_id=7,
            is_self=True,
            relationship_type=RelationshipType.SELF,
        )
        listed = self.client.get(
            "/internal/cards/?beneficiary_id=7",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listed.data), 2)

    def test_manual_review_author_cannot_create_card(self):
        author = make_principal(
            12, Role.AUTHOR, email="review@test.com", status=UserStatus.MANUAL_REVIEW
        )
        self.client.force_authenticate(author)
        response = self.client.post(
            "/api/cards/",
            {
                "recipient_session_token": "missing",
                "target_amount": "100000.00",
                "end_date": "2027-01-01",
                "description": "Help",
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

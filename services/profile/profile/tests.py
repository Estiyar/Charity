from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import (
    RelationshipType,
    RepresentationMethod,
    RepresentationStatus,
    Role,
)
from ekomek_common.masking import mask_iin
from ekomek_common.outbox_app.models import OutboxEvent

RECIPIENT_IIN = "850315301234"
CHILD_IIN = "120315301234"
OTHER_IIN = "750315301234"


def upsert_payload(owner_id, iin, relationship, snapshot=None, method=None):
    body = {
        "owner_user_id": owner_id,
        "iin": iin,
        "relationship_type": relationship,
        "snapshot": snapshot or {
            "full_name": "Получатель",
            "birth_date": "2012-03-15",
            "age": 14,
            "gender": "female",
            "city": "Алматы",
            "clinic": "Клиника",
            "diagnosis": "Онкология",
            "source": "dev",
            "found": True,
            "iin_hash": "med-ref",
            "requires_manual_review": False,
        },
    }
    if method:
        body["verification_method"] = method
    return body


class BeneficiaryRepresentationTestCase(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com", full_name="Автор")
        self.other_author = make_principal(12, Role.AUTHOR, email="other@test.com", full_name="Другой")
        self.donor = make_principal(5, Role.DONOR, email="donor@test.com")
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com", full_name="Модератор")

    def upsert(self, **kwargs):
        return self.client.post(
            "/internal/beneficiaries/",
            upsert_payload(self.author.id, **kwargs),
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )

    def test_self_representation_is_verified(self):
        response = self.upsert(iin=RECIPIENT_IIN, relationship=RelationshipType.SELF, method=RepresentationMethod.ECP)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["representation"]["verification_status"], RepresentationStatus.VERIFIED)
        self.assertEqual(response.data["representation"]["verification_method"], RepresentationMethod.ECP)
        self.assertTrue(response.data["medical_linked"])
        self.assertEqual(response.data["iin_masked"], mask_iin(RECIPIENT_IIN))
        self.assertNotIn(RECIPIENT_IIN, str({k: v for k, v in response.data.items() if k != "iin"}))
        self.assertTrue(OutboxEvent.objects.filter(event_type="beneficiary.created").exists())
        self.assertTrue(OutboxEvent.objects.filter(event_type="representation.verified").exists())

    def test_child_external_source_stays_pending(self):
        response = self.upsert(
            iin=CHILD_IIN,
            relationship=RelationshipType.PARENT,
            method=RepresentationMethod.EXTERNAL_SOURCE,
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["representation"]["verification_status"], RepresentationStatus.PENDING)
        self.assertEqual(response.data["representation"]["verification_method"], RepresentationMethod.EXTERNAL_SOURCE)

    def test_other_person_beneficiary_ecp_is_verified(self):
        response = self.upsert(
            iin=OTHER_IIN,
            relationship=RelationshipType.REPRESENTATIVE,
            method=RepresentationMethod.ECP,
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["representation"]["verification_status"], RepresentationStatus.VERIFIED)

    def test_one_author_can_manage_multiple_beneficiaries(self):
        self.upsert(iin=CHILD_IIN, relationship=RelationshipType.PARENT, method=RepresentationMethod.DOCUMENT)
        self.upsert(iin=OTHER_IIN, relationship=RelationshipType.REPRESENTATIVE, method=RepresentationMethod.MANUAL_REVIEW)
        self.client.force_authenticate(self.author)
        listed = self.client.get("/api/beneficiaries")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 2)

    def test_donor_cannot_list_beneficiaries(self):
        self.client.force_authenticate(self.donor)
        response = self.client.get("/api/beneficiaries")
        self.assertEqual(response.status_code, 403)

    def test_public_visibility_hides_private_fields(self):
        created = self.upsert(iin=CHILD_IIN, relationship=RelationshipType.PARENT, method=RepresentationMethod.DOCUMENT)
        beneficiary_id = created.data["id"]
        self.client.force_authenticate(self.author)
        self.client.patch(
            f"/api/beneficiaries/{beneficiary_id}",
            {"public_fields": ["full_name", "city"]},
            format="json",
        )
        self.client.force_authenticate(None)
        public = self.client.get(f"/api/beneficiaries/{beneficiary_id}")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.data["full_name"], "Получатель")
        self.assertEqual(public.data["city"], "Алматы")
        self.assertNotIn("diagnosis", public.data)
        self.assertNotIn("iin_masked", public.data)
        self.assertNotIn(CHILD_IIN, str(public.data))

    def test_document_submit_and_moderator_confirm(self):
        created = self.upsert(iin=CHILD_IIN, relationship=RelationshipType.PARENT, method=RepresentationMethod.DOCUMENT)
        representation_id = created.data["representation"]["id"]
        self.client.force_authenticate(self.author)
        submitted = self.client.post(
            "/api/representations/verify",
            {
                "representation_id": representation_id,
                "verification_method": RepresentationMethod.DOCUMENT,
                "document_ids": [4, 8],
            },
            format="json",
        )
        self.assertEqual(submitted.status_code, 200, submitted.data)
        self.assertEqual(submitted.data["verification_status"], RepresentationStatus.MANUAL_REVIEW)
        self.assertEqual(submitted.data["document_ids"], [4, 8])
        self.assertTrue(OutboxEvent.objects.filter(event_type="representation.submitted").exists())
        self.client.force_authenticate(self.moderator)
        queue = self.client.get("/api/representations/moderation")
        self.assertEqual(len(queue.data), 1)
        confirmed = self.client.post(f"/api/representations/{representation_id}/confirm", {}, format="json")
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.data["verification_status"], RepresentationStatus.VERIFIED)
        self.assertEqual(confirmed.data["verified_by"], self.moderator.id)

    def test_moderator_reject_requires_reason(self):
        created = self.upsert(
            iin=CHILD_IIN,
            relationship=RelationshipType.GUARDIAN,
            method=RepresentationMethod.MANUAL_REVIEW,
        )
        representation_id = created.data["representation"]["id"]
        self.client.force_authenticate(self.moderator)
        missing = self.client.post(f"/api/representations/{representation_id}/reject", {}, format="json")
        self.assertEqual(missing.status_code, 400)
        rejected = self.client.post(
            f"/api/representations/{representation_id}/reject",
            {"reason": "Документы не подтверждают опеку"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(rejected.data["verification_status"], RepresentationStatus.REJECTED)
        self.assertEqual(rejected.data["rejection_reason"], "Документы не подтверждают опеку")
        self.assertTrue(OutboxEvent.objects.filter(event_type="representation.rejected").exists())

    def test_other_author_cannot_see_private_beneficiary(self):
        created = self.upsert(iin=CHILD_IIN, relationship=RelationshipType.PARENT, method=RepresentationMethod.DOCUMENT)
        self.client.force_authenticate(self.other_author)
        listed = self.client.get("/api/beneficiaries")
        self.assertEqual(listed.data, [])
        detail = self.client.get(f"/api/beneficiaries/{created.data['id']}")
        self.assertNotIn("iin_masked", detail.data)

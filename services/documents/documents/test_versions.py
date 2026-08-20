from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role

from .models import Document, DocumentAuditEvent, DocumentStatus, DocumentVersion


def pdf_file(name, content=b"%PDF-same"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


class VersionedDocumentTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        self.other = make_principal(12, Role.AUTHOR, email="other@test.com")
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com")
        self.cards = {
            1: {"id": 1, "author_id": 11, "status": "draft"},
            2: {"id": 2, "author_id": 11, "status": "active"},
            3: {"id": 3, "author_id": 12, "status": "draft"},
        }
        patcher = patch("documents.access_services.cards_client")
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        mocked.return_value.get.side_effect = self._fetch_card

    def _fetch_card(self, path, **kwargs):
        card_id = int(path.rstrip("/").split("/")[-1])
        return self.cards[card_id]

    def _upload(self, card_id=1, uploaded=None, extra=None):
        self.client.force_authenticate(self.author)
        payload = {"file": uploaded or pdf_file("scan.pdf", b"%PDF-one"), "document_type": "medical"}
        payload.update(extra or {})
        return self.client.post(f"/api/cards/{card_id}/documents/", payload, format="multipart")

    def test_new_version_keeps_previous_file(self):
        first = self._upload(uploaded=pdf_file("old.pdf", b"%PDF-old-bytes"))
        self.assertEqual(first.status_code, 201, first.data)
        document_id = first.data["id"]
        first_version = DocumentVersion.objects.get(document_id=document_id, version_number=1)
        original_name = first_version.original_file.name
        original_bytes = first_version.original_file.read()
        second = self._upload(
            uploaded=pdf_file("new.pdf", b"%PDF-new-bytes"),
            extra={"supersedes_document_id": document_id, "issuer": "Клиника №1"},
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["id"], document_id)
        self.assertEqual(second.data["version_number"], 2)
        self.assertEqual(Document.objects.filter(card_id=1).count(), 1)
        self.assertEqual(DocumentVersion.objects.filter(document_id=document_id).count(), 2)
        first_version.refresh_from_db()
        self.assertEqual(first_version.original_file.name, original_name)
        first_version.original_file.open("rb")
        self.assertEqual(first_version.original_file.read(), original_bytes)
        versions = self.client.get(f"/api/documents/{document_id}/versions/")
        self.assertEqual(len(versions.data), 2)
        self.assertEqual(versions.data[1]["supersedes_version_id"], first_version.id)

    def test_same_card_duplicate_hash_is_rejected(self):
        first = self._upload(uploaded=pdf_file("a.pdf", b"%PDF-dup"))
        self.assertEqual(first.status_code, 201, first.data)
        second = self._upload(uploaded=pdf_file("b.pdf", b"%PDF-dup"))
        self.assertEqual(second.status_code, 400)

    def test_invalid_type_and_size_are_rejected(self):
        self.client.force_authenticate(self.author)
        bad_type = self.client.post(
            "/api/cards/1/documents/",
            {"file": SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")},
            format="multipart",
        )
        self.assertEqual(bad_type.status_code, 400)
        with override_settings(MAX_UPLOAD_SIZE_MB=0):
            too_big = self.client.post(
                "/api/cards/1/documents/",
                {"file": pdf_file("big.pdf", b"%PDF-x")},
                format="multipart",
            )
        self.assertEqual(too_big.status_code, 400)

    def test_public_payload_redacts_sensitive_data(self):
        uploaded = self._upload(
            card_id=2,
            uploaded=pdf_file("iin-850315301234.pdf", b"%PDF-850315301234"),
            extra={
                "issuer": "Клиника 850315301234",
                "visibility": "public",
            },
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        document = Document.objects.get(pk=uploaded.data["id"])
        document.current_version.verification_status = DocumentStatus.VERIFIED
        document.current_version.save(update_fields=["verification_status"])
        self.client.force_authenticate(None)
        public = self.client.get("/api/cards/2/documents/public/")
        self.assertEqual(public.status_code, 200, public.data)
        payload = public.data[0]
        self.assertNotIn("original_url", payload)
        self.assertNotIn("file_hash", payload)
        self.assertNotIn("file_name", payload)
        self.assertNotIn("850315301234", str(payload))
        self.assertIn("********1234", payload["issuer"])
        self.assertTrue(payload["public_file_url"])
        document.current_version.public_file.open("rb")
        self.assertNotEqual(document.current_version.public_file.read(), b"%PDF-850315301234")
        original = self.client.get(f"/api/documents/{document.id}/original/")
        self.assertEqual(original.status_code, 404)

    def test_staff_and_author_can_open_original(self):
        created = self._upload(uploaded=pdf_file("secret.pdf", b"%PDF-secret-original"))
        document_id = created.data["id"]
        author_file = self.client.get(f"/api/documents/{document_id}/original/")
        self.assertEqual(author_file.status_code, 200)
        self.assertEqual(b"".join(author_file.streaming_content), b"%PDF-secret-original")
        self.client.force_authenticate(self.moderator)
        staff_file = self.client.get(f"/api/documents/{document_id}/original/")
        self.assertEqual(staff_file.status_code, 200)
        self.assertEqual(b"".join(staff_file.streaming_content), b"%PDF-secret-original")
        self.client.force_authenticate(self.other)
        denied = self.client.get(f"/api/documents/{document_id}/original/")
        self.assertEqual(denied.status_code, 404)
        self.assertTrue(DocumentAuditEvent.objects.filter(event_type="original_accessed").exists())

    def test_audit_log_is_immutable(self):
        created = self._upload()
        event = DocumentAuditEvent.objects.get(document_id=created.data["id"], event_type="uploaded")
        with self.assertRaises(ValueError):
            event.summary = "hack"
            event.save()
        with self.assertRaises(ValueError):
            event.delete()

    def test_expired_current_version_loses_verified_status(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        created = self._upload(
            extra={"expires_at": yesterday.isoformat(), "visibility": "public"}
        )
        document = Document.objects.get(pk=created.data["id"])
        version = document.current_version
        version.verification_status = DocumentStatus.VERIFIED
        version.expires_at = yesterday
        version.save(update_fields=["verification_status", "expires_at"])
        listed = self.client.get("/api/cards/1/documents/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]["verification_status"], DocumentStatus.EXPIRED)
        self.assertTrue(DocumentAuditEvent.objects.filter(event_type="expired").exists())

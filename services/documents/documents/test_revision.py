from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.comments import CommentType
from ekomek_common.constants import Role
from ekomek_common.outbox_app.models import OutboxEvent

from .comment_models import DocumentModeratorComment
from .models import Document, DocumentStatus, DocumentVersion


def pdf_file(name, content=b"%PDF-doc"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


class DocumentRevisionWorkflowTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        self.other = make_principal(12, Role.AUTHOR, email="other@test.com")
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.cards = {
            1: {"id": 1, "author_id": 11, "status": "draft"},
            3: {"id": 3, "author_id": 12, "status": "draft"},
        }
        patcher = patch("documents.access_services.cards_client")
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        mocked.return_value.get.side_effect = self._fetch_card

    def _fetch_card(self, path, **kwargs):
        card_id = int(path.rstrip("/").split("/")[-1])
        return self.cards[card_id]

    def _upload(self, card_id=1, uploaded=None):
        self.client.force_authenticate(self.author)
        return self.client.post(
            f"/api/cards/{card_id}/documents/",
            {"file": uploaded or pdf_file("scan.pdf"), "document_type": "medical"},
            format="multipart",
        )

    def test_revision_then_new_version_keeps_history(self):
        created = self._upload()
        self.assertEqual(created.status_code, 201, created.data)
        document_id = created.data["id"]
        self.client.force_authenticate(self.moderator)
        denied = self.client.post(f"/api/documents/{document_id}/request-revision/", {}, format="json")
        self.assertEqual(denied.status_code, 400)
        revised = self.client.post(
            f"/api/documents/{document_id}/request-revision/",
            {"revision_comment": "Скан нечитаемый", "internal_comment": "возможно подделка"},
            format="json",
        )
        self.assertEqual(revised.status_code, 200, revised.data)
        self.assertEqual(revised.data["verification_status"], DocumentStatus.REVISION_REQUIRED)
        self.assertTrue(OutboxEvent.objects.filter(event_type="document.revision_required").exists())
        staff_types = {item["comment_type"] for item in revised.data["comments"]}
        self.assertEqual(staff_types, {CommentType.REVISION, CommentType.INTERNAL})

        self.client.force_authenticate(self.author)
        author_docs = self.client.get("/api/cards/1/documents/")
        types = {item["comment_type"] for item in author_docs.data[0]["comments"]}
        self.assertEqual(types, {CommentType.REVISION})
        self.assertNotIn("возможно подделка", str(author_docs.data))

        self.client.force_authenticate(self.other)
        foreign = self.client.get("/api/cards/1/documents/")
        self.assertEqual(foreign.status_code, 403)

        self.client.force_authenticate(self.author)
        replaced = self.client.post(
            "/api/cards/1/documents/",
            {
                "file": pdf_file("fixed.pdf", b"%PDF-fixed"),
                "supersedes_document_id": document_id,
            },
            format="multipart",
        )
        self.assertEqual(replaced.status_code, 201, replaced.data)
        self.assertEqual(replaced.data["id"], document_id)
        self.assertEqual(replaced.data["version_number"], 2)
        self.assertEqual(DocumentVersion.objects.filter(document_id=document_id).count(), 2)
        self.assertEqual(Document.objects.get(pk=document_id).moderator_comments.count(), 2)
        old_version = DocumentVersion.objects.get(document_id=document_id, version_number=1)
        self.assertEqual(old_version.verification_status, DocumentStatus.REVISION_REQUIRED)
        self.assertEqual(old_version.moderator_comment, "Скан нечитаемый")

        comment = DocumentModeratorComment.objects.get(comment_type=CommentType.REVISION)
        self.client.force_authenticate(self.moderator)
        edited = self.client.patch(
            f"/api/documents/{document_id}/comments/{comment.id}/",
            {"body": "Нужен цветной скан"},
            format="json",
        )
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(len(edited.data["edits"]), 1)

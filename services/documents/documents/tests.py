from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role

from .models import Document


class DocumentsHealthTest(APITestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)


class DocumentHashMatchTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com")
        cards = {
            1: {"id": 1, "author_id": 11, "status": "draft"},
            2: {"id": 2, "author_id": 11, "status": "draft"},
        }

        def fetch_card(path, **kwargs):
            card_id = int(path.rstrip("/").split("/")[-1])
            return cards[card_id]

        patcher = patch("documents.access_services.cards_client")
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        mocked.return_value.get.side_effect = fetch_card

    def test_same_file_hash_matches_other_card(self):
        self.client.force_authenticate(self.author)
        payload = {"file": SimpleUploadedFile("scan.pdf", b"same-bytes", content_type="application/pdf")}
        first = self.client.post("/api/cards/1/documents/", payload, format="multipart")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(
            "/api/cards/2/documents/",
            {"file": SimpleUploadedFile("copy.pdf", b"same-bytes", content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(second.status_code, 201, second.data)
        first_hash = Document.objects.get(pk=first.data["id"]).current_version.file_hash
        second_hash = Document.objects.get(pk=second.data["id"]).current_version.file_hash
        self.assertEqual(first_hash, second_hash)
        matches = self.client.get(
            "/internal/documents/duplicates/?card_id=2",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(matches.status_code, 200)
        self.assertEqual(matches.data[0]["card_id"], 1)
        self.assertNotIn("file_url", matches.data[0])

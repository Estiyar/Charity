from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cards.models import FundraisingCard
from apps.documents.models import Document, DocumentStatus

User = get_user_model()


class DocumentAPITestCase(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор Тест",
            role="author",
        )
        self.other_author = User.objects.create_user(
            email="other@example.com",
            password="securepass123",
            full_name="Другой Автор",
            role="author",
        )
        self.card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Айгуль Смагулова",
            diagnosis="Онкология",
            city="Алматы",
            target_amount="500000.00",
            end_date=date.today() + timedelta(days=90),
            iin_encrypted="990101300123",
            document_number_encrypted="12345678",
            contact_phone="+7 777 123 45 67",
        )

    def test_upload_pdf_document(self):
        pdf = SimpleUploadedFile(
            "report.pdf",
            b"%PDF-1.4 test content",
            content_type="application/pdf",
        )
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.card.id}/documents/",
            {"file": pdf},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["file_type"], "pdf")
        self.assertEqual(self.card.documents.count(), 1)

    def test_upload_photo_sets_card_photo(self):
        image = SimpleUploadedFile(
            "photo.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.card.id}/documents/",
            {"file": image},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.card.refresh_from_db()
        self.assertTrue(self.card.photo_url)

    def test_upload_invalid_extension_rejected(self):
        doc = SimpleUploadedFile(
            "virus.exe",
            b"bad",
            content_type="application/octet-stream",
        )
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.card.id}/documents/",
            {"file": doc},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_oversized_file_rejected(self):
        large = SimpleUploadedFile(
            "big.pdf",
            BytesIO(b"x" * (11 * 1024 * 1024)).read(),
            content_type="application/pdf",
        )
        self.client.force_authenticate(user=self.author)
        response = self.client.post(
            f"/api/cards/{self.card.id}/documents/",
            {"file": large},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_documents_for_owner(self):
        pdf = SimpleUploadedFile("report.pdf", b"%PDF-1.4", content_type="application/pdf")
        self.client.force_authenticate(user=self.author)
        self.client.post(
            f"/api/cards/{self.card.id}/documents/",
            {"file": pdf},
            format="multipart",
        )

        response = self.client.get(f"/api/cards/{self.card.id}/documents/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_documents_hidden_for_other_author(self):
        self.client.force_authenticate(user=self.other_author)
        response = self.client.get(f"/api/cards/{self.card.id}/documents/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_foreign_card_not_found(self):
        pdf = SimpleUploadedFile("report.pdf", b"%PDF-1.4", content_type="application/pdf")
        self.client.force_authenticate(user=self.other_author)
        response = self.client.post(
            f"/api/cards/{self.card.id}/documents/",
            {"file": pdf},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DocumentModerationAPITestCase(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="Автор",
            role="author",
        )
        self.moderator = User.objects.create_user(
            email="mod@example.com",
            password="securepass123",
            full_name="Модератор",
            role="moderator",
        )
        self.card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Тест",
            diagnosis="Тест",
            city="Алматы",
            target_amount="100000.00",
            end_date=date.today() + timedelta(days=30),
        )
        pdf = SimpleUploadedFile("report.pdf", b"%PDF-1.4", content_type="application/pdf")
        self.document = Document.objects.create(
            card=self.card,
            file_url=pdf,
            file_name="report.pdf",
            file_type="pdf",
            status=DocumentStatus.UPLOADED,
        )

    def test_verify_document(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/documents/{self.document.id}/verify/",
            {"has_confidential": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], DocumentStatus.VERIFIED)
        self.document.refresh_from_db()
        self.assertTrue(self.document.has_confidential)

    def test_reject_document_requires_comment(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/documents/{self.document.id}/reject/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_document_with_comment(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/documents/{self.document.id}/reject/",
            {"comment": "Документ нечитаемый"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], DocumentStatus.REJECTED)
        self.document.refresh_from_db()
        self.assertEqual(self.document.moderator_comment, "Документ нечитаемый")

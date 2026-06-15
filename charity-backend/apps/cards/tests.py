from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.common.card_status import CardStatus
from apps.common.masking import mask_iin, mask_phone

from .models import FundraisingCard

User = get_user_model()


class CardAPITestCase(APITestCase):
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
        self.donor = User.objects.create_user(
            email="donor@example.com",
            password="securepass123",
            full_name="Донор Тест",
            role="donor",
        )
        self.moderator = User.objects.create_user(
            email="mod@example.com",
            password="securepass123",
            full_name="Модератор Тест",
            role="moderator",
        )
        self.card_payload = {
            "full_name": "Айгуль Смагулова",
            "diagnosis": "Онкология",
            "city": "Алматы",
            "clinic": "Городская поликлиника",
            "age": 8,
            "gender": "female",
            "description": "Нужна помощь на лечение",
            "target_amount": "500000.00",
            "end_date": (date.today() + timedelta(days=90)).isoformat(),
            "iin": "990101300123",
            "document_number": "12345678",
            "contact_phone": "+7 777 123 45 67",
            "contact_email": "family@example.com",
            "personal_data_consent": True,
        }

    def _create_card(self, author=None, card_status=None):
        author = author or self.author
        self.client.force_authenticate(user=author)
        response = self.client.post("/api/cards/", self.card_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(user=None)
        card = FundraisingCard.objects.get(pk=response.data["id"])
        if card_status:
            card.status = card_status
            card.save(update_fields=["status"])
        return card

    def test_create_card_text_only(self):
        self.client.force_authenticate(user=self.author)
        payload = {
            "full_name": "Тест Получатель",
            "diagnosis": "ДЦП",
            "city": "Астана",
            "target_amount": "100000.00",
            "end_date": (date.today() + timedelta(days=30)).isoformat(),
            "personal_data_consent": "true",
        }
        response = self.client.post("/api/cards/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], CardStatus.DRAFT)

    def test_create_card_with_photo(self):
        self.client.force_authenticate(user=self.author)
        photo = SimpleUploadedFile(
            "photo.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )
        payload = {
            "full_name": "Тест С Фото",
            "diagnosis": "Онкология",
            "city": "Алматы",
            "target_amount": "200000.00",
            "end_date": (date.today() + timedelta(days=60)).isoformat(),
            "personal_data_consent": "true",
            "photo_url": photo,
        }
        response = self.client.post("/api/cards/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        card = FundraisingCard.objects.get(pk=response.data["id"])
        self.assertTrue(card.photo_url)

    def test_create_card_author_only(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post("/api/cards/", self.card_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], CardStatus.DRAFT)
        self.assertEqual(response.data["iin"], "990101300123")

        card = FundraisingCard.objects.get(pk=response.data["id"])
        self.assertEqual(card.author, self.author)
        self.assertEqual(card.iin_masked, mask_iin("990101300123"))

    def test_create_card_all_fields(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post("/api/cards/", self.card_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], CardStatus.DRAFT)

        card = FundraisingCard.objects.get(pk=response.data["id"])
        self.assertEqual(card.full_name, self.card_payload["full_name"])
        self.assertEqual(card.diagnosis, self.card_payload["diagnosis"])
        self.assertEqual(card.city, self.card_payload["city"])
        self.assertEqual(card.clinic, self.card_payload["clinic"])
        self.assertEqual(card.age, self.card_payload["age"])
        self.assertEqual(card.gender, self.card_payload["gender"])
        self.assertEqual(card.description, self.card_payload["description"])
        self.assertEqual(str(card.target_amount), self.card_payload["target_amount"])
        self.assertEqual(card.end_date.isoformat(), self.card_payload["end_date"])
        self.assertEqual(card.iin_encrypted, self.card_payload["iin"])
        self.assertEqual(card.document_number_encrypted, self.card_payload["document_number"])
        self.assertEqual(card.contact_phone, self.card_payload["contact_phone"])
        self.assertEqual(card.contact_email, self.card_payload["contact_email"])
        self.assertEqual(card.status, CardStatus.DRAFT)

    def test_create_card_requires_consent(self):
        self.client.force_authenticate(user=self.author)
        payload = {**self.card_payload, "personal_data_consent": False}
        response = self.client.post("/api/cards/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("personal_data_consent", response.data)

    def test_create_card_rejected_for_donor(self):
        self.client.force_authenticate(user=self.donor)
        response = self.client.post("/api/cards/", self.card_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_shows_public_cards_only_for_anonymous(self):
        public_card = self._create_card(card_status=CardStatus.ACTIVE)
        self._create_card()

        response = self.client.get("/api/cards/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(public_card.id, ids)
        self.assertEqual(len(ids), 1)

    def test_author_sees_own_draft_in_list(self):
        draft = self._create_card()
        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/cards/")

        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(draft.id, ids)

    def test_other_author_cannot_view_foreign_draft(self):
        draft = self._create_card(author=self.other_author)
        self.client.force_authenticate(user=self.author)
        response = self.client.get(f"/api/cards/{draft.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_detail_masks_confidential_data(self):
        card = self._create_card(card_status=CardStatus.ACTIVE)
        card.iin_encrypted = "990101300123"
        card.document_number_encrypted = "12345678"
        card.contact_phone = "+7 777 123 45 67"
        card.save()

        response = self.client.get(f"/api/cards/{card.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["iin_masked"], mask_iin("990101300123"))
        self.assertEqual(response.data["contact_phone"], mask_phone("+7 777 123 45 67"))
        self.assertNotIn("iin", response.data)

    def test_owner_sees_full_confidential_data(self):
        card = self._create_card()
        self.client.force_authenticate(user=self.author)
        response = self.client.get(f"/api/cards/{card.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["iin"], "990101300123")
        self.assertEqual(response.data["contact_phone"], "+7 777 123 45 67")

    def test_moderator_sees_full_confidential_data(self):
        card = self._create_card()
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(f"/api/cards/{card.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["iin"], "990101300123")

    def test_update_own_card(self):
        card = self._create_card()
        self.client.force_authenticate(user=self.author)
        response = self.client.put(
            f"/api/cards/{card.id}/",
            {**self.card_payload, "full_name": "Новое Имя"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Новое Имя")

    def test_update_foreign_card_returns_not_found(self):
        card = self._create_card(author=self.other_author)
        self.client.force_authenticate(user=self.author)
        response = self.client.put(
            f"/api/cards/{card.id}/",
            {**self.card_payload, "full_name": "Взлом"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_draft(self):
        card = self._create_card()
        self.client.force_authenticate(user=self.author)
        response = self.client.delete(f"/api/cards/{card.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FundraisingCard.objects.filter(pk=card.id).exists())

    def test_delete_non_draft_rejected(self):
        card = self._create_card()
        card.status = CardStatus.PENDING_MODERATION
        card.save(update_fields=["status"])
        self.client.force_authenticate(user=self.author)
        response = self.client.delete(f"/api/cards/{card.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_draft_to_pending_moderation(self):
        card = self._create_card()
        self.client.force_authenticate(user=self.author)
        response = self.client.post(f"/api/cards/{card.id}/submit/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], CardStatus.PENDING_MODERATION)
        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.PENDING_MODERATION)

    def test_submit_invalid_status_rejected(self):
        card = self._create_card()
        card.status = CardStatus.ACTIVE
        card.save(update_fields=["status"])
        self.client.force_authenticate(user=self.author)
        response = self.client.post(f"/api/cards/{card.id}/submit/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_city(self):
        card = self._create_card()
        card.status = CardStatus.ACTIVE
        card.save(update_fields=["status"])

        response = self.client.get("/api/cards/", {"city": "Алматы"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_my_cards_returns_all_statuses(self):
        draft = self._create_card()
        pending = self._create_card()
        pending.status = CardStatus.PENDING_MODERATION
        pending.save(update_fields=["status"])
        active = self._create_card()
        active.status = CardStatus.ACTIVE
        active.save(update_fields=["status"])

        self.client.force_authenticate(user=self.author)
        response = self.client.get("/api/cards/my/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data}
        self.assertEqual(returned_ids, {draft.id, pending.id, active.id})
        statuses = {item["status"] for item in response.data}
        self.assertEqual(
            statuses,
            {CardStatus.DRAFT, CardStatus.PENDING_MODERATION, CardStatus.ACTIVE},
        )

    def test_my_cards_not_accessible_by_donor(self):
        self.client.force_authenticate(user=self.donor)
        response = self.client.get("/api/cards/my/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

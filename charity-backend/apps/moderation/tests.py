from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus
from apps.donations.serializers import DONATION_SUCCESS_MESSAGE
from apps.expenses.models import ExpenseStatus
from apps.moderation.models import ModerationLog, RedistributionDecision
from apps.users.models import Role

User = get_user_model()

CARD_PAYLOAD = {
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


class ModerationAPITestCase(APITestCase):
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
        self.donor = User.objects.create_user(
            email="donor@example.com",
            password="securepass123",
            full_name="Донор",
            role="donor",
        )
        self.card = FundraisingCard.objects.create(
            author=self.author,
            full_name="Айгуль Смагулова",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("500000.00"),
            end_date=date.today() + timedelta(days=90),
            status=CardStatus.PENDING_MODERATION,
            iin_encrypted="990101300123",
            document_number_encrypted="12345678",
            contact_phone="+7 777 123 45 67",
        )

    def test_moderator_can_list_pending_cards(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get("/api/moderation/cards/?status=pending_moderation")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_non_moderator_cannot_access_moderation(self):
        self.client.force_authenticate(user=self.donor)
        response = self.client.get("/api/moderation/cards/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_sees_full_card_data(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(f"/api/moderation/cards/{self.card.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["iin"], "990101300123")
        self.assertEqual(response.data["contact_phone"], "+7 777 123 45 67")

    def test_approve_moves_card_to_active(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(f"/api/moderation/cards/{self.card.id}/approve/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], CardStatus.ACTIVE)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.ACTIVE)
        self.assertEqual(ModerationLog.objects.filter(card=self.card, action="approve").count(), 1)

    def test_reject_requires_comment(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(f"/api/moderation/cards/{self.card.id}/reject/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_with_comment(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/moderation/cards/{self.card.id}/reject/",
            {"comment": "Недостаточно документов"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], CardStatus.REJECTED)
        self.card.refresh_from_db()
        self.assertEqual(self.card.moderator_comment, "Недостаточно документов")

    def test_request_revision_with_comment(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(
            f"/api/moderation/cards/{self.card.id}/request-revision/",
            {"comment": "Уточните диагноз"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], CardStatus.REVISION_REQUIRED)
        self.card.refresh_from_db()
        self.assertEqual(self.card.moderator_comment, "Уточните диагноз")

    def test_author_sees_moderator_comment_on_own_card(self):
        self.card.status = CardStatus.REVISION_REQUIRED
        self.card.moderator_comment = "Уточните диагноз"
        self.card.save(update_fields=["status", "moderator_comment"])
        self.client.force_authenticate(user=self.author)
        response = self.client.get(f"/api/cards/{self.card.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["moderator_comment"], "Уточните диагноз")


class Section30ScenarioAPITestCase(APITestCase):
    def _login(self, email, password):
        response = self.client.post(
            "/api/auth/login",
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    def test_scenario_1_create(self):
        register_response = self.client.post(
            "/api/auth/register",
            {
                "full_name": "Сценарий Автор",
                "email": "scenario1@example.com",
                "phone": "+7 777 000 00 01",
                "password": "securepass123",
                "repeat_password": "securepass123",
                "role": Role.AUTHOR,
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        self._login("scenario1@example.com", "securepass123")

        create_response = self.client.post("/api/cards/", CARD_PAYLOAD, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["status"], CardStatus.DRAFT)
        card_id = create_response.data["id"]

        submit_response = self.client.post(f"/api/cards/{card_id}/submit/", format="json")
        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_response.data["status"], CardStatus.PENDING_MODERATION)

        card = FundraisingCard.objects.get(pk=card_id)
        self.assertEqual(card.status, CardStatus.PENDING_MODERATION)

    def test_scenario_2_moderation(self):
        author = User.objects.create_user(
            email="scenario2-author@example.com",
            password="securepass123",
            full_name="Автор Сценарий 2",
            role=Role.AUTHOR,
        )
        moderator = User.objects.create_user(
            email="scenario2-mod@example.com",
            password="securepass123",
            full_name="Модератор Сценарий 2",
            role=Role.MODERATOR,
        )
        card = FundraisingCard.objects.create(
            author=author,
            full_name=CARD_PAYLOAD["full_name"],
            diagnosis=CARD_PAYLOAD["diagnosis"],
            city=CARD_PAYLOAD["city"],
            clinic=CARD_PAYLOAD["clinic"],
            age=CARD_PAYLOAD["age"],
            gender=CARD_PAYLOAD["gender"],
            description=CARD_PAYLOAD["description"],
            target_amount=Decimal(CARD_PAYLOAD["target_amount"]),
            end_date=date.fromisoformat(CARD_PAYLOAD["end_date"]),
            iin_encrypted=CARD_PAYLOAD["iin"],
            document_number_encrypted=CARD_PAYLOAD["document_number"],
            contact_phone=CARD_PAYLOAD["contact_phone"],
            contact_email=CARD_PAYLOAD["contact_email"],
            status=CardStatus.PENDING_MODERATION,
        )

        self._login("scenario2-mod@example.com", "securepass123")

        list_response = self.client.get("/api/moderation/cards/?status=pending_moderation")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item["id"] == card.id for item in list_response.data))

        detail_response = self.client.get(f"/api/moderation/cards/{card.id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["iin"], CARD_PAYLOAD["iin"])

        approve_response = self.client.post(
            f"/api/moderation/cards/{card.id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], CardStatus.ACTIVE)

        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.ACTIVE)

        self.client.credentials()
        public_response = self.client.get("/api/cards/")
        self.assertEqual(public_response.status_code, status.HTTP_200_OK)
        public_ids = [item["id"] for item in public_response.data["results"]]
        self.assertIn(card.id, public_ids)

    def test_scenario_3_donation(self):
        author = User.objects.create_user(
            email="scenario3-author@example.com",
            password="securepass123",
            full_name="Автор Сценарий 3",
            role=Role.AUTHOR,
        )
        card = FundraisingCard.objects.create(
            author=author,
            full_name="Активный сбор",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("500000.00"),
            collected_amount=Decimal("10000.00"),
            end_date=date.today() + timedelta(days=90),
            status=CardStatus.ACTIVE,
        )

        donate_response = self.client.post(
            f"/api/cards/{card.id}/donate/",
            {
                "amount": "5000.00",
                "donor_name": "Иван Донор",
                "contact": "+7 777 111 22 33",
                "payment_method": "card",
                "personal_data_consent": True,
            },
            format="json",
        )
        self.assertEqual(donate_response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Спасибо за помощь", donate_response.data["message"])
        self.assertEqual(donate_response.data["message"], DONATION_SUCCESS_MESSAGE)
        self.assertEqual(donate_response.data["collected_amount"], "15000.00")

        card.refresh_from_db()
        self.assertEqual(card.collected_amount, Decimal("15000.00"))

        donations_response = self.client.get(f"/api/cards/{card.id}/donations/")
        self.assertEqual(donations_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(donations_response.data), 1)
        self.assertEqual(donations_response.data[0]["donor_name"], "Иван Донор")
        self.assertEqual(donations_response.data[0]["amount"], "5000.00")

    def test_scenario_4_expense(self):
        author = User.objects.create_user(
            email="scenario4-author@example.com",
            password="securepass123",
            full_name="Автор Сценарий 4",
            role=Role.AUTHOR,
        )
        moderator = User.objects.create_user(
            email="scenario4-mod@example.com",
            password="securepass123",
            full_name="Модератор Сценарий 4",
            role=Role.MODERATOR,
        )
        card = FundraisingCard.objects.create(
            author=author,
            full_name="Активный сбор расходов",
            diagnosis="Онкология",
            city="Алматы",
            target_amount=Decimal("500000.00"),
            collected_amount=Decimal("50000.00"),
            end_date=date.today() + timedelta(days=90),
            status=CardStatus.ACTIVE,
        )

        self._login("scenario4-author@example.com", "securepass123")
        expense_response = self.client.post(
            f"/api/cards/{card.id}/expenses/",
            {
                "date": str(date.today()),
                "purpose": "Лекарства",
                "amount": "10000.00",
                "comment": "Аптека",
            },
            format="json",
        )
        self.assertEqual(expense_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(expense_response.data["status"], ExpenseStatus.PENDING)
        expense_id = expense_response.data["id"]

        self.client.credentials()
        public_before = self.client.get(f"/api/cards/{card.id}/expenses/")
        self.assertEqual(public_before.status_code, status.HTTP_200_OK)
        self.assertEqual(len(public_before.data), 0)

        self._login("scenario4-mod@example.com", "securepass123")
        approve_response = self.client.post(
            f"/api/expenses/{expense_id}/approve/",
            {},
            format="json",
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data["status"], ExpenseStatus.APPROVED)

        self.client.credentials()
        public_after = self.client.get(f"/api/cards/{card.id}/expenses/")
        self.assertEqual(public_after.status_code, status.HTTP_200_OK)
        self.assertEqual(len(public_after.data), 1)
        self.assertEqual(public_after.data[0]["id"], expense_id)
        self.assertEqual(public_after.data[0]["status"], ExpenseStatus.APPROVED)

    def test_scenario_5_redistribution(self):
        author = User.objects.create_user(
            email="scenario5-author@example.com",
            password="securepass123",
            full_name="Автор Сценарий 5",
            role=Role.AUTHOR,
        )
        moderator = User.objects.create_user(
            email="scenario5-mod@example.com",
            password="securepass123",
            full_name="Модератор Сценарий 5",
            role=Role.MODERATOR,
        )
        card = FundraisingCard.objects.create(
            author=author,
            full_name="Сбор для перераспределения",
            diagnosis="ДЦП",
            city="Астана",
            target_amount=Decimal("300000.00"),
            collected_amount=Decimal("80000.00"),
            end_date=date.today() + timedelta(days=60),
            status=CardStatus.ACTIVE,
        )

        self._login("scenario5-mod@example.com", "securepass123")
        decision_response = self.client.post(
            f"/api/cards/{card.id}/redistribution/",
            {"decision_type": "fund", "comment": "Передать в общий фонд"},
            format="json",
        )
        self.assertEqual(decision_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(decision_response.data["decision_type"], "fund")

        self.assertEqual(RedistributionDecision.objects.filter(card=card).count(), 1)
        decision = RedistributionDecision.objects.get(card=card)
        self.assertEqual(decision.decision_type, RedistributionDecision.DecisionType.FUND)
        self.assertEqual(decision.comment, "Передать в общий фонд")

        card.refresh_from_db()
        self.assertEqual(card.status, CardStatus.REDISTRIBUTION)

        self.client.credentials()
        history_response = self.client.get(f"/api/cards/{card.id}/redistribution/")
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(history_response.data["decisions"]), 1)
        self.assertEqual(history_response.data["decisions"][0]["id"], decision.id)
        self.assertEqual(history_response.data["decisions"][0]["decision_type"], "fund")

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.constants import Role, UserStatus
from ekomek_common.outbox_app.models import OutboxEvent

from .models import User


class InternalUserCorrectionTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="author@example.com",
            password="securepass123",
            full_name="СТАРОЕ ИМЯ",
            role=Role.AUTHOR,
            iin="870308301456",
            birth_date="1990-01-15",
        )

    def test_internal_patch_updates_locked_fields_and_audits(self):
        response = self.client.patch(
            f"/internal/users/{self.user.id}/",
            {"full_name": "ИВАНОВ ИВАН", "birth_date": "1988-04-20"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["full_name"], "ИВАНОВ ИВАН")
        self.assertEqual(response.data["birth_date"], "1988-04-20")
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "ИВАНОВ ИВАН")
        event = OutboxEvent.objects.filter(event_type="user.updated", aggregate_id=str(self.user.id)).last()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload["actor"], "internal")

    def test_list_filters_by_status(self):
        User.objects.create_user(
            email="review@example.com",
            password="securepass123",
            full_name="На проверке",
            role=Role.AUTHOR,
            iin="870308301457",
            status=UserStatus.MANUAL_REVIEW,
        )
        response = self.client.get(
            "/internal/users/?status=manual_review",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], "review@example.com")

    def test_set_status_is_idempotent(self):
        first = self.client.post(
            f"/internal/users/{self.user.id}/set-status/",
            {"status": UserStatus.BLOCKED, "reason": "risk"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        second = self.client.post(
            f"/internal/users/{self.user.id}/set-status/",
            {"status": UserStatus.BLOCKED, "reason": "risk"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.status, UserStatus.BLOCKED)
        events = OutboxEvent.objects.filter(event_type="user.status_changed", aggregate_id=str(self.user.id))
        self.assertEqual(events.count(), 1)

    def test_set_status_without_token_is_forbidden(self):
        response = self.client.post(
            f"/internal/users/{self.user.id}/set-status/",
            {"status": UserStatus.BLOCKED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_internal_patch_without_token_is_forbidden(self):
        response = self.client.patch(
            f"/internal/users/{self.user.id}/",
            {"full_name": "ИВАНОВ ИВАН"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_internal_credit_rejects_donor_refund(self):
        response = self.client.post(
            f"/internal/users/{self.user.id}/credit/",
            {"amount": "100.00", "purpose": "donor_refund", "description": "Возврат по сбору"},
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, 0)

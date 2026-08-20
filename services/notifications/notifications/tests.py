from unittest.mock import Mock, patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import Role

from notifications.models import Notification, NotificationDelivery
from notifications.services import (
    create_notification,
    on_card_revision_required,
    on_document_expired,
    on_expense_revision_required,
    on_invoice_rejected,
    on_payment_failed,
    on_payment_succeeded,
    on_report_resolved,
    send_delivery,
)
from notifications.tasks import notify_upcoming_deadlines_task


class NotificationsHealthTest(APITestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)


class NotificationCenterApiTest(APITestCase):
    def setUp(self):
        self.user = make_principal(11, Role.AUTHOR, email="author@test.com", full_name="Автор")
        self.other = make_principal(22, Role.DONOR, email="donor@test.com", full_name="Донор")
        user_patch = patch("notifications.services.identity_client")
        self.mock_identity = user_patch.start()
        self.mock_identity.return_value.get.side_effect = lambda path: {
            "id": 11 if path.endswith("/11/") else 22,
            "email": "author@test.com" if path.endswith("/11/") else "donor@test.com",
        }
        self.addCleanup(user_patch.stop)

    def create_item(self, recipient_id, key):
        return create_notification(
            recipient_id=recipient_id,
            title="Test",
            body="Body",
            notification_type="test.notice",
            event_type="test.notice",
            payload={"card_id": 1},
            idempotency_key=key,
        )

    def test_notification_creation_is_idempotent(self):
        first = self.create_item(11, "same-key")
        second = self.create_item(11, "same-key")
        self.assertEqual(first.id, second.id)
        self.assertEqual(Notification.objects.count(), 1)

    def test_list_only_returns_own_notifications(self):
        self.create_item(11, "mine-1")
        self.create_item(22, "other-1")
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["recipient"], 11)

    def test_list_is_paginated(self):
        for index in range(13):
            self.create_item(11, f"n-{index}")
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/notifications")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 13)
        self.assertEqual(len(response.data["results"]), 12)
        self.assertEqual(response.data["unread_count"], 13)

    def test_mark_read_unread_and_read_all(self):
        item = self.create_item(11, "toggle")
        self.client.force_authenticate(self.user)
        read_response = self.client.post(f"/api/notifications/{item.id}/read")
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.is_read)
        unread_response = self.client.post(f"/api/notifications/{item.id}/unread")
        self.assertEqual(unread_response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertFalse(item.is_read)
        self.create_item(11, "toggle-2")
        all_response = self.client.post("/api/notifications/read-all")
        self.assertEqual(all_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(recipient_id=11, is_read=False).count(), 0)

    def test_other_user_cannot_mark_read(self):
        item = self.create_item(11, "private-item")
        self.client.force_authenticate(self.other)
        response = self.client.post(f"/api/notifications/{item.id}/read")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DeliveryTest(APITestCase):
    def setUp(self):
        user_patch = patch("notifications.services.identity_client")
        self.mock_identity = user_patch.start()
        self.mock_identity.return_value.get.return_value = {"id": 11, "email": "author@test.com"}
        self.addCleanup(user_patch.stop)

    def test_create_notification_creates_delivery_rows(self):
        item = create_notification(
            recipient_id=11,
            title="Test",
            body="Body",
            notification_type="test.notice",
            event_type="test.notice",
            payload={"card_id": 1},
            idempotency_key="delivery-rows",
        )
        self.assertEqual(item.deliveries.count(), 3)
        self.assertEqual(item.deliveries.filter(status=NotificationDelivery.Status.PENDING).count(), 1)
        self.assertEqual(item.deliveries.filter(status=NotificationDelivery.Status.SKIPPED).count(), 2)

    def test_send_delivery_marks_sent(self):
        item = create_notification(
            recipient_id=11,
            title="Test",
            body="Body",
            notification_type="test.notice",
            event_type="test.notice",
            payload={"card_id": 1},
            idempotency_key="send-success",
        )
        delivery = item.deliveries.get(channel="email")
        send_delivery(delivery)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)
        self.assertEqual(delivery.attempt_count, 1)

    def test_send_delivery_retries_then_fails(self):
        item = create_notification(
            recipient_id=11,
            title="Test",
            body="Body",
            notification_type="test.notice",
            event_type="test.notice",
            payload={"card_id": 1},
            idempotency_key="send-fail",
        )
        delivery = item.deliveries.get(channel="email")
        with patch("notifications.services.get_delivery_adapter") as adapter_factory:
            failing_adapter = Mock()
            failing_adapter.send.side_effect = RuntimeError("adapter failed")
            adapter_factory.return_value = failing_adapter
            send_delivery(delivery)
            send_delivery(delivery)
            send_delivery(delivery)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, NotificationDelivery.Status.FAILED)
        self.assertEqual(delivery.attempt_count, 3)
        self.assertEqual(delivery.logs.count(), 3)


class EventHandlerTest(APITestCase):
    def setUp(self):
        user_patch = patch("notifications.services.identity_client")
        self.mock_identity = user_patch.start()
        self.mock_identity.return_value.get.side_effect = lambda path: {
            "id": 11 if path.endswith("/11/") else 21,
            "email": "author@test.com" if path.endswith("/11/") else "donor@test.com",
        }
        self.addCleanup(user_patch.stop)

        card_patch = patch("notifications.services.cards_client")
        self.mock_cards = card_patch.start()
        self.mock_cards.return_value.get.return_value = {
            "id": 5,
            "author_id": 11,
            "target_amount": "100.00",
            "collected_amount": "100.00",
            "end_date": "2026-08-20",
        }
        self.addCleanup(card_patch.stop)

    def test_revision_events_create_author_notifications(self):
        on_card_revision_required({"author_id": 11, "card_id": 5, "revision_comment": "Исправьте диагноз"})
        on_expense_revision_required({"author_id": 11, "expense_id": 3, "card_id": 5, "revision_comment": "Нужен чек"})
        items = list(Notification.objects.filter(recipient_id=11).order_by("id"))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].notification_type, "card.revision_required")
        self.assertIn("Исправьте диагноз", items[0].body)

    def test_payment_failed_notifies_donor(self):
        on_payment_failed(
            {
                "donation_id": 7,
                "donor_id": 21,
                "email": "donor@test.com",
                "status": "failed",
                "reason": "Повторите оплату",
            }
        )
        item = Notification.objects.get(recipient_id=21)
        self.assertEqual(item.notification_type, "payment.failed")
        self.assertIn("Повторите оплату", item.body)

    def test_payment_succeeded_creates_donation_and_milestone_notifications(self):
        on_payment_succeeded(
            {
                "donation_id": 7,
                "card_id": 5,
                "amount": "100.00",
                "currency": "KZT",
            }
        )
        types = list(Notification.objects.filter(recipient_id=11).values_list("notification_type", flat=True))
        self.assertIn("payment.succeeded", types)
        self.assertIn("fundraising.progress", types)

    def test_document_expired_and_invoice_rejected(self):
        on_document_expired({"document_id": 9, "card_id": 5})
        on_invoice_rejected({"invoice_id": 4, "card_id": 5, "reason": "Неверная сумма"})
        self.assertEqual(Notification.objects.filter(recipient_id=11).count(), 2)

    def test_report_resolved_notifies_reporter(self):
        on_report_resolved({"report_id": 8, "card_id": 5, "reporter_user_id": 21, "resolution": "Жалоба подтверждена"})
        item = Notification.objects.get(recipient_id=21)
        self.assertEqual(item.notification_type, "report.resolved")


class DeadlineTaskTest(APITestCase):
    def setUp(self):
        user_patch = patch("notifications.services.identity_client")
        self.mock_identity = user_patch.start()
        self.mock_identity.return_value.get.return_value = {"id": 11, "email": "author@test.com"}
        self.addCleanup(user_patch.stop)

    def test_upcoming_deadline_task_creates_once(self):
        with patch("notifications.tasks.cards_client") as cards:
            cards.return_value.get.return_value = [
                {"id": 5, "author_id": 11, "end_date": "2026-08-20"},
                {"id": 6, "author_id": 11, "end_date": "2026-09-30"},
            ]
            with patch("django.utils.timezone.localdate") as localdate:
                from datetime import date

                localdate.return_value = date(2026, 8, 18)
                notify_upcoming_deadlines_task()
                notify_upcoming_deadlines_task()
        self.assertEqual(Notification.objects.filter(notification_type="card.deadline_approaching").count(), 1)


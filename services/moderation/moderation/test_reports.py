from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.constants import CardStatus, Role
from ekomek_common.outbox_app.models import OutboxEvent
from ekomek_common.reports import ReportCategory, ReportStatus

from .report_models import UserReport
from .report_services import calculate_report_risk, create_user_report


class FakeRequest:
    def __init__(self, user=None, fingerprint="127.0.0.1:test"):
        self.user = user
        self.data = {"reporter_fingerprint": fingerprint}
        self.headers = {}
        self.META = {"REMOTE_ADDR": "127.0.0.1"}


class ModerationReportsTest(APITestCase):
    def setUp(self):
        self.moderator = make_principal(31, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.reporter = make_principal(21, Role.DONOR, email="reporter@test.com")
        cards = patch("moderation.report_services.cards_client")
        fetch = patch("moderation.report_services.fetch_card")
        self.cards_client = cards.start()
        self.fetch_card = fetch.start()
        self.addCleanup(cards.stop)
        self.addCleanup(fetch.stop)
        self.fetch_card.return_value = {
            "id": 5,
            "status": CardStatus.ACTIVE,
            "full_name": "Test",
        }
        self.cards_client.return_value.post.return_value = {"id": 5, "status": CardStatus.SUSPENDED}

    def test_repeated_reports_do_not_inflate_risk(self):
        UserReport.objects.create(
            card_id=5,
            reporter_user_id=self.reporter.id,
            reporter_key=f"user:{self.reporter.id}",
            category=ReportCategory.SUSPECTED_FRAUD,
            description="First report with enough text",
        )
        UserReport.objects.create(
            card_id=5,
            reporter_user_id=self.reporter.id,
            reporter_key=f"user:{self.reporter.id}",
            category=ReportCategory.OTHER,
            description="Second report with enough text",
        )
        score, unique = calculate_report_risk(5)
        self.assertEqual(unique, 1)
        self.assertEqual(score, 40)

    def test_unique_reporters_increase_risk(self):
        UserReport.objects.create(
            card_id=5,
            reporter_key="user:1",
            category=ReportCategory.SUSPECTED_FRAUD,
            description="First report with enough text",
        )
        UserReport.objects.create(
            card_id=5,
            reporter_key="user:2",
            category=ReportCategory.OTHER,
            description="Second report with enough text",
        )
        score, unique = calculate_report_risk(5)
        self.assertEqual(unique, 2)
        self.assertEqual(score, 45)

    def test_create_report_syncs_risk_and_auto_suspends_serious_category(self):
        request = FakeRequest(user=self.reporter, fingerprint="guest:abc")
        report = create_user_report(
            card_id=5,
            category=ReportCategory.STOLEN_PHOTOS,
            description="Фотографии взяты с чужого профиля без разрешения",
            request=request,
        )
        self.assertEqual(report.category, ReportCategory.STOLEN_PHOTOS)
        paths = [call.args[0] for call in self.cards_client.return_value.post.call_args_list]
        self.assertIn("/internal/cards/5/report-risk/", paths)
        self.assertIn("/internal/cards/5/suspend/", paths)
        self.assertTrue(OutboxEvent.objects.filter(event_type="report.created").exists())

    def test_moderation_report_queue_and_resolve(self):
        report = UserReport.objects.create(
            card_id=5,
            reporter_user_id=self.reporter.id,
            reporter_key=f"user:{self.reporter.id}",
            category=ReportCategory.DOCUMENT_ISSUE,
            description="Документ выглядит подделанным по качеству",
        )
        self.client.force_authenticate(self.moderator)
        listed = self.client.get("/api/moderation/reports/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        items = listed.data if isinstance(listed.data, list) else listed.data.get("results", [])
        self.assertEqual(len(items), 1)

        resolved = self.client.post(
            f"/api/moderation/reports/{report.id}/resolve/",
            {"status": ReportStatus.RESOLVED, "resolution": "Проверили документ, всё корректно"},
            format="json",
        )
        self.assertEqual(resolved.status_code, status.HTTP_200_OK, resolved.data)
        report.refresh_from_db()
        self.assertEqual(report.status, ReportStatus.RESOLVED)
        self.assertTrue(OutboxEvent.objects.filter(event_type="report.resolved").exists())

    def test_internal_create_report_endpoint(self):
        response = self.client.post(
            "/internal/reports/",
            {
                "card_id": 5,
                "category": ReportCategory.OTHER,
                "description": "Другая проблема с описанием сбора",
                "reporter_fingerprint": "guest:xyz",
            },
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

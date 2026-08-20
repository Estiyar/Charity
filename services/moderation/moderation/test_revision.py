from unittest.mock import patch

from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.comments import CommentType
from ekomek_common.constants import CardStatus, Role
from ekomek_common.outbox_app.models import OutboxEvent

from .comment_models import ModerationComment
from .models import ManualReviewCase


class FakeCardsClient:
    def __init__(self):
        self.card = {
            "id": 9,
            "full_name": "Карточка",
            "status": CardStatus.PENDING_MODERATION,
            "author_id": 11,
            "author_full_name": "Автор",
        }
        self.posts = []

    def get(self, path, **kwargs):
        return dict(self.card)

    def post(self, path, json=None, **kwargs):
        self.posts.append((path, json or {}))
        if "transition" in path:
            self.card["status"] = json["status"]
            self.card["moderator_comment"] = json.get("revision_comment") or json.get("comment") or ""
            return dict(self.card)
        return dict(self.card)


class CardRevisionModerationTest(APITestCase):
    def setUp(self):
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        self.fake = FakeCardsClient()
        cards = patch("moderation.services.cards_client")
        docs = patch("moderation.services.documents_client")
        mocked_cards = cards.start()
        mocked_docs = docs.start()
        self.addCleanup(cards.stop)
        self.addCleanup(docs.stop)
        mocked_cards.return_value = self.fake
        mocked_docs.return_value.get.return_value = []

    def test_request_revision_without_comment_is_rejected(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.post("/api/moderation/cards/9/request-revision/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.fake.card["status"], CardStatus.PENDING_MODERATION)

    def test_request_revision_sends_typed_comments(self):
        self.client.force_authenticate(self.moderator)
        response = self.client.post(
            "/api/moderation/cards/9/request-revision/",
            {
                "revision_comment": "Добавьте документы",
                "internal_comment": "Проверить ИИН отдельно",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.fake.card["status"], CardStatus.REVISION_REQUIRED)
        _path, payload = self.fake.posts[-1]
        self.assertEqual(payload["revision_comment"], "Добавьте документы")
        self.assertEqual(payload["internal_comment"], "Проверить ИИН отдельно")
        self.assertEqual(payload["comment_author_id"], 22)
        self.assertTrue(OutboxEvent.objects.filter(event_type="moderation.decision_created").exists())

    def test_manual_review_revision_keeps_comment_history(self):
        case = ManualReviewCase.objects.create(
            subject_type=ManualReviewCase.SubjectType.CARD,
            subject_id=9,
            subject_label="Карточка",
            status=ManualReviewCase.Status.OPEN,
        )
        self.fake.card["status"] = CardStatus.MANUAL_REVIEW
        self.client.force_authenticate(self.moderator)
        first = self.client.post(
            f"/api/moderation/reviews/{case.id}/request-revision/",
            {"comment": "Нужны справки", "internal_comment": "не публиковать"},
            format="json",
        )
        self.assertEqual(first.status_code, 200, first.data)
        case.refresh_from_db()
        self.assertEqual(case.status, ManualReviewCase.Status.REVISION_REQUIRED)
        comments = ModerationComment.objects.filter(target_type="review", target_id=case.id)
        self.assertEqual(comments.count(), 2)
        types = set(comments.values_list("comment_type", flat=True))
        self.assertEqual(types, {CommentType.REVISION, CommentType.INTERNAL})
        listed = self.client.get(f"/api/moderation/comments/?target_type=review&target_id={case.id}")
        self.assertEqual(len(listed.data), 2)
        revision = comments.get(comment_type=CommentType.REVISION)
        edited = self.client.patch(
            f"/api/moderation/comments/{revision.id}/",
            {"body": "Нужны справки и фото"},
            format="json",
        )
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(len(edited.data["edits"]), 1)
        detail = self.client.get(f"/api/moderation/reviews/{case.id}/")
        self.assertEqual(len(detail.data["comments"]), 2)
        self.assertEqual(len(detail.data["audit_history"]), 1)

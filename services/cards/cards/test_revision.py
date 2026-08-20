from datetime import date
from decimal import Decimal
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from ekomek_common.auth import make_principal
from ekomek_common.comments import CommentType
from ekomek_common.constants import CardStatus, RelationshipType, Role
from ekomek_common.outbox_app.models import OutboxEvent

from .comment_models import CardModeratorComment
from .models import FundraisingCard


class CardRevisionWorkflowTest(APITestCase):
    def setUp(self):
        self.author = make_principal(11, Role.AUTHOR, email="author@test.com", full_name="Автор")
        self.other = make_principal(12, Role.AUTHOR, email="other@test.com")
        self.moderator = make_principal(22, Role.MODERATOR, email="mod@test.com", full_name="Модератор")
        docs = patch("cards.duplicate_services.documents_client")
        self.documents_client = docs.start()
        self.addCleanup(docs.stop)
        self.documents_client.return_value.get.return_value = []
        for target in (
            "cards.trust_services.identity_client",
            "cards.trust_services.profile_client",
            "cards.trust_services.documents_client",
            "cards.trust_services.expenses_client",
        ):
            mocked = patch(target)
            client = mocked.start()
            self.addCleanup(mocked.stop)
            client.return_value.get.return_value = {}
        self.card = FundraisingCard.objects.create(
            author_id=self.author.id,
            author_email=self.author.email,
            full_name="Test",
            diagnosis="X",
            city="Almaty",
            target_amount=Decimal("1000"),
            end_date=date(2027, 1, 1),
            status=CardStatus.PENDING_MODERATION,
            is_self=True,
            relationship_type=RelationshipType.SELF,
        )

    def _transition(self, **payload):
        return self.client.post(
            f"/internal/cards/{self.card.id}/transition/",
            payload,
            format="json",
            HTTP_X_INTERNAL_TOKEN="dev-internal-token",
        )

    def test_revision_requires_comment_and_hides_internal_from_author(self):
        revised = self._transition(
            status=CardStatus.REVISION_REQUIRED,
            revision_comment="Исправьте диагноз",
            internal_comment="Похоже на дубль",
            comment_author_id=self.moderator.id,
            comment_author_role=Role.MODERATOR,
            comment_author_name="Модератор",
        )
        self.assertEqual(revised.status_code, status.HTTP_200_OK, revised.data)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.REVISION_REQUIRED)
        self.assertEqual(self.card.moderator_comment, "Исправьте диагноз")
        self.assertTrue(
            OutboxEvent.objects.filter(event_type="card.revision_required", aggregate_id=str(self.card.id)).exists()
        )

        self.client.force_authenticate(self.author)
        author_view = self.client.get(f"/api/cards/{self.card.id}/")
        self.assertEqual(author_view.status_code, status.HTTP_200_OK)
        self.assertEqual(author_view.data["moderator_comment"], "Исправьте диагноз")
        types = {item["comment_type"] for item in author_view.data["comments"]}
        self.assertEqual(types, {CommentType.REVISION})
        self.assertNotIn("Похоже на дубль", str(author_view.data))

        self.client.force_authenticate(self.other)
        foreign = self.client.get(f"/api/cards/{self.card.id}/")
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(self.moderator)
        staff_view = self.client.get(f"/api/cards/{self.card.id}/")
        staff_types = {item["comment_type"] for item in staff_view.data["comments"]}
        self.assertEqual(staff_types, {CommentType.REVISION, CommentType.INTERNAL})

    def test_author_edits_allowed_fields_and_resubmits_keeping_history(self):
        self._transition(
            status=CardStatus.REVISION_REQUIRED,
            revision_comment="Уточните описание",
            internal_comment="внутренняя заметка",
        )
        self.client.force_authenticate(self.author)
        patched = self.client.patch(
            f"/api/cards/{self.card.id}/",
            {"description": "Обновлённое описание лечения"},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.data)
        submitted = self.client.post(f"/api/cards/{self.card.id}/submit/")
        self.assertEqual(submitted.status_code, status.HTTP_200_OK, submitted.data)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, CardStatus.PENDING_MODERATION)
        self.assertEqual(self.card.moderator_comments.count(), 2)
        self.assertEqual(self.card.description, "Обновлённое описание лечения")

    def test_staff_comment_edit_writes_history(self):
        self._transition(status=CardStatus.REVISION_REQUIRED, revision_comment="Старый текст")
        comment = CardModeratorComment.objects.get(comment_type=CommentType.REVISION)
        self.client.force_authenticate(self.moderator)
        edited = self.client.patch(
            f"/api/cards/{self.card.id}/comments/{comment.id}/",
            {"body": "Новый текст"},
            format="json",
        )
        self.assertEqual(edited.status_code, status.HTTP_200_OK, edited.data)
        self.assertEqual(edited.data["body"], "Новый текст")
        self.assertEqual(len(edited.data["edits"]), 1)
        self.assertEqual(edited.data["edits"][0]["previous_body"], "Старый текст")
        self.client.force_authenticate(self.author)
        author_view = self.client.get(f"/api/cards/{self.card.id}/")
        self.assertEqual(author_view.data["moderator_comment"], "Новый текст")
        self.assertEqual(author_view.data["comments"][0]["edits"][0]["previous_body"], "Старый текст")

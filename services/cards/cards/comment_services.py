from django.utils import timezone
from rest_framework import serializers

from ekomek_common.comments import CommentType, comment_author_fields, editor_fields, visible_comment_types

from .comment_models import CardCommentEdit, CardModeratorComment


class CardCommentEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardCommentEdit
        fields = ("id", "editor_id", "editor_role", "editor_name", "previous_body", "new_body", "created_at")
        read_only_fields = fields


class CardCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    type = serializers.CharField(source="comment_type")
    target_type = serializers.SerializerMethodField()
    target_id = serializers.IntegerField(source="card_id")
    edits = CardCommentEditSerializer(many=True, read_only=True)

    class Meta:
        model = CardModeratorComment
        fields = (
            "id",
            "author",
            "author_id",
            "author_role",
            "author_name",
            "target_type",
            "target_id",
            "type",
            "comment_type",
            "body",
            "created_at",
            "edited_at",
            "edits",
        )
        read_only_fields = fields

    def get_author(self, obj):
        return {"id": obj.author_id, "role": obj.author_role, "name": obj.author_name}

    def get_target_type(self, obj):
        return "card"


def serialize_card_comments(card, *, user=None, include_internal=False):
    types = visible_comment_types(user, include_internal=include_internal)
    comments = card.moderator_comments.filter(comment_type__in=types).prefetch_related("edits")
    return CardCommentSerializer(comments, many=True).data


def record_card_comments(card, *, revision_body, internal_body="", actor=None, extra_author=None):
    created = []
    author = comment_author_fields(actor, **(extra_author or {}))
    if revision_body:
        created.append(
            CardModeratorComment.objects.create(
                card=card,
                comment_type=CommentType.REVISION,
                body=revision_body,
                **author,
            )
        )
    if internal_body:
        created.append(
            CardModeratorComment.objects.create(
                card=card,
                comment_type=CommentType.INTERNAL,
                body=internal_body,
                **author,
            )
        )
    return created


def apply_transition_comments(card, data, *, actor=None):
    from ekomek_common.comments import CommentActor, resolve_revision_comment

    revision_body, internal_body = resolve_revision_comment(data)
    comment_actor = CommentActor(data, actor)
    extra = {
        "author_id": comment_actor.id,
        "author_role": comment_actor.role,
        "author_name": comment_actor.full_name,
    }
    return record_card_comments(
        card,
        revision_body=revision_body,
        internal_body=internal_body,
        extra_author=extra,
    )


def edit_card_comment(comment, body, *, actor=None):
    body = (body or "").strip()
    if not body:
        raise ValueError("Текст комментария обязателен.")
    previous = comment.body
    if previous == body:
        return comment
    CardCommentEdit.objects.create(
        comment=comment,
        previous_body=previous,
        new_body=body,
        **editor_fields(actor),
    )
    comment.body = body
    comment.edited_at = timezone.now()
    comment.save(update_fields=["body", "edited_at"])
    if comment.comment_type == CommentType.REVISION:
        comment.card.moderator_comment = body
        comment.card.save(update_fields=["moderator_comment", "updated_at"])
    return comment

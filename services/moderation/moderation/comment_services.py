from django.utils import timezone
from rest_framework import serializers

from ekomek_common.comments import CommentType, comment_author_fields, editor_fields, visible_comment_types

from .comment_models import ModerationComment, ModerationCommentEdit


class ModerationCommentEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModerationCommentEdit
        fields = ("id", "editor_id", "editor_role", "editor_name", "previous_body", "new_body", "created_at")
        read_only_fields = fields


class StoredModerationCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    type = serializers.CharField(source="comment_type")
    edits = ModerationCommentEditSerializer(many=True, read_only=True)

    class Meta:
        model = ModerationComment
        fields = (
            "id",
            "author",
            "author_id",
            "author_role",
            "author_name",
            "target_type",
            "target_id",
            "review_id",
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


def list_moderation_comments(target_type, target_id, *, user=None, include_internal=False):
    types = visible_comment_types(user, include_internal=include_internal)
    comments = ModerationComment.objects.filter(
        target_type=target_type,
        target_id=target_id,
        comment_type__in=types,
    ).prefetch_related("edits")
    return StoredModerationCommentSerializer(comments, many=True).data


def record_moderation_comments(
    *,
    target_type,
    target_id,
    revision_body,
    internal_body="",
    actor=None,
    review_id=None,
):
    created = []
    author = comment_author_fields(actor)
    if revision_body:
        created.append(
            ModerationComment.objects.create(
                target_type=target_type,
                target_id=target_id,
                review_id=review_id,
                comment_type=CommentType.REVISION,
                body=revision_body,
                **author,
            )
        )
    if internal_body:
        created.append(
            ModerationComment.objects.create(
                target_type=target_type,
                target_id=target_id,
                review_id=review_id,
                comment_type=CommentType.INTERNAL,
                body=internal_body,
                **author,
            )
        )
    return created


def edit_moderation_comment(comment, body, *, actor=None):
    body = (body or "").strip()
    if not body:
        raise ValueError("Текст комментария обязателен.")
    previous = comment.body
    if previous == body:
        return comment
    ModerationCommentEdit.objects.create(
        comment=comment,
        previous_body=previous,
        new_body=body,
        **editor_fields(actor),
    )
    comment.body = body
    comment.edited_at = timezone.now()
    comment.save(update_fields=["body", "edited_at"])
    return comment

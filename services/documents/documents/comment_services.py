from django.utils import timezone
from rest_framework import serializers

from ekomek_common.comments import CommentType, comment_author_fields, editor_fields, visible_comment_types

from .comment_models import DocumentCommentEdit, DocumentModeratorComment


class DocumentCommentEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCommentEdit
        fields = ("id", "editor_id", "editor_role", "editor_name", "previous_body", "new_body", "created_at")
        read_only_fields = fields


class DocumentCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    type = serializers.CharField(source="comment_type")
    target_type = serializers.SerializerMethodField()
    target_id = serializers.IntegerField(source="document_id")
    edits = DocumentCommentEditSerializer(many=True, read_only=True)

    class Meta:
        model = DocumentModeratorComment
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
        return "document"


def serialize_document_comments(document, *, user=None, include_internal=False):
    types = visible_comment_types(user, include_internal=include_internal)
    comments = document.moderator_comments.filter(comment_type__in=types).prefetch_related("edits")
    return DocumentCommentSerializer(comments, many=True).data


def record_document_comments(document, *, revision_body, internal_body="", actor=None):
    created = []
    author = comment_author_fields(actor)
    if revision_body:
        created.append(
            DocumentModeratorComment.objects.create(
                document=document,
                comment_type=CommentType.REVISION,
                body=revision_body,
                **author,
            )
        )
    if internal_body:
        created.append(
            DocumentModeratorComment.objects.create(
                document=document,
                comment_type=CommentType.INTERNAL,
                body=internal_body,
                **author,
            )
        )
    return created


def edit_document_comment(comment, body, *, actor=None):
    body = (body or "").strip()
    if not body:
        raise ValueError("Текст комментария обязателен.")
    previous = comment.body
    if previous == body:
        return comment
    DocumentCommentEdit.objects.create(
        comment=comment,
        previous_body=previous,
        new_body=body,
        **editor_fields(actor),
    )
    comment.body = body
    comment.edited_at = timezone.now()
    comment.save(update_fields=["body", "edited_at"])
    version = comment.document.current_version
    if comment.comment_type == CommentType.REVISION and version is not None:
        version.moderator_comment = body
        version.save(update_fields=["moderator_comment", "updated_at"])
    return comment

from django.db import models

from ekomek_common.comments import CommentType


class ModerationComment(models.Model):
    class TargetType(models.TextChoices):
        CARD = "card", "card"
        EXPENSE = "expense", "expense"
        DOCUMENT = "document", "document"
        REVIEW = "review", "review"

    target_type = models.CharField(max_length=16, choices=TargetType.choices)
    target_id = models.IntegerField()
    review_id = models.IntegerField(null=True, blank=True)
    comment_type = models.CharField(max_length=32, choices=[(item, item) for item in CommentType.ALL])
    author_id = models.IntegerField()
    author_role = models.CharField(max_length=32, blank=True)
    author_name = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "moderation_comment"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
        ]


class ModerationCommentEdit(models.Model):
    comment = models.ForeignKey(ModerationComment, on_delete=models.CASCADE, related_name="edits")
    editor_id = models.IntegerField()
    editor_role = models.CharField(max_length=32, blank=True)
    editor_name = models.CharField(max_length=255, blank=True)
    previous_body = models.TextField()
    new_body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "moderation_commentedit"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("История правки комментария неизменяема.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("История правки комментария неизменяема.")

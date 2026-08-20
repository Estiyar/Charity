from django.db import models

from ekomek_common.comments import CommentType


class DocumentModeratorComment(models.Model):
    document = models.ForeignKey("Document", on_delete=models.CASCADE, related_name="moderator_comments")
    comment_type = models.CharField(max_length=32, choices=[(item, item) for item in CommentType.ALL])
    author_id = models.IntegerField()
    author_role = models.CharField(max_length=32, blank=True)
    author_name = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "documents_moderatorcomment"
        ordering = ["created_at", "id"]


class DocumentCommentEdit(models.Model):
    comment = models.ForeignKey(DocumentModeratorComment, on_delete=models.CASCADE, related_name="edits")
    editor_id = models.IntegerField()
    editor_role = models.CharField(max_length=32, blank=True)
    editor_name = models.CharField(max_length=255, blank=True)
    previous_body = models.TextField()
    new_body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_commentedit"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("История правки комментария неизменяема.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("История правки комментария неизменяема.")

from django.core.files.storage import FileSystemStorage
from django.db import models
from django.conf import settings


def private_document_storage():
    return FileSystemStorage(location=str(settings.PRIVATE_MEDIA_ROOT), base_url=None)


def original_upload_path(instance, filename):
    return _version_path(instance, "original", filename)


def public_upload_path(instance, filename):
    return _version_path(instance, "public", filename)


def _version_path(instance, kind, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    card_id = instance.document.card_id if instance.document_id else "pending"
    document_id = instance.document_id or "pending"
    return f"documents/{kind}/{card_id}/{document_id}/{instance.version_number}.{extension}"


class DocumentType(models.TextChoices):
    MEDICAL = "medical", "Медицинский"
    DIAGNOSIS = "diagnosis", "Диагноз"
    CLINIC = "clinic", "Клиника"
    IDENTITY = "identity", "Удостоверение"
    REPRESENTATION = "representation", "Представительство"
    OTHER = "other", "Другое"


class DocumentVisibility(models.TextChoices):
    STAFF = "staff", "Сотрудники"
    AUTHOR = "author", "Автор"
    PUBLIC = "public", "Публичный"


class DocumentStatus(models.TextChoices):
    UPLOADED = "uploaded", "Загружен"
    UNDER_REVIEW = "under_review", "На проверке"
    REVISION_REQUIRED = "revision_required", "На доработке"
    VERIFIED = "verified", "Проверен"
    REJECTED = "rejected", "Отклонён"
    EXPIRED = "expired", "Истёк"


class Document(models.Model):
    card_id = models.IntegerField(db_index=True)
    document_type = models.CharField(max_length=32, choices=DocumentType.choices, default=DocumentType.MEDICAL)
    visibility = models.CharField(max_length=16, choices=DocumentVisibility.choices, default=DocumentVisibility.PUBLIC)
    current_version = models.ForeignKey(
        "DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents_document"
        ordering = ["-created_at"]


class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    issued_at = models.DateField(null=True, blank=True)
    issuer = models.CharField(max_length=255, blank=True)
    verification_status = models.CharField(
        max_length=32,
        choices=DocumentStatus.choices,
        default=DocumentStatus.UPLOADED,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by_id = models.IntegerField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="superseded_by",
    )
    file_hash = models.CharField(max_length=64, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    visibility = models.CharField(max_length=16, choices=DocumentVisibility.choices, default=DocumentVisibility.PUBLIC)
    original_file = models.FileField(upload_to=original_upload_path, storage=private_document_storage)
    public_file = models.FileField(upload_to=public_upload_path, blank=True)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=32)
    has_confidential = models.BooleanField(default=True)
    moderator_comment = models.TextField(blank=True)
    uploaded_by_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents_documentversion"
        ordering = ["version_number", "id"]
        unique_together = ("document", "version_number")

    @property
    def status(self):
        return self.verification_status


class DocumentAuditEvent(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="audit_events")
    version = models.ForeignKey(
        DocumentVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=64, db_index=True)
    summary = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_documentauditevent"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Журнал документа неизменяем.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Журнал документа неизменяем.")


from .comment_models import DocumentCommentEdit, DocumentModeratorComment  # noqa: E402,F401

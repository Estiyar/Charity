from django.db import models
from apps.cards.models import FundraisingCard


class DocumentStatus(models.TextChoices):
    UPLOADED = "uploaded", "Загружен"
    UNDER_REVIEW = "under_review", "На проверке"
    VERIFIED = "verified", "Проверен"
    REJECTED = "rejected", "Отклонён"


class Document(models.Model):
    card = models.ForeignKey(FundraisingCard, on_delete=models.CASCADE, related_name="documents")
    file_url = models.FileField(upload_to="cards/documents/")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=32)  # pdf / jpg / png
    status = models.CharField(max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.UPLOADED)
    has_confidential = models.BooleanField(default=False)  # ТЗ раздел 11
    moderator_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.file_name} ({self.status})"

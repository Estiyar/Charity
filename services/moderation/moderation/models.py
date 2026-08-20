from django.db import models


class ModerationLog(models.Model):
    card_id = models.IntegerField(db_index=True)
    card_name = models.CharField(max_length=255, blank=True)
    moderator_id = models.IntegerField(null=True, blank=True)
    moderator_name = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=64)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "moderation_log"
        ordering = ["-created_at"]


class ManualReviewCase(models.Model):
    class SubjectType(models.TextChoices):
        USER = "user", "user"
        CARD = "card", "card"

    class Status(models.TextChoices):
        OPEN = "open", "open"
        APPROVED = "approved", "approved"
        REJECTED = "rejected", "rejected"
        REVISION_REQUIRED = "revision_required", "revision_required"
        SUSPENDED = "suspended", "suspended"

    subject_type = models.CharField(max_length=16, choices=SubjectType.choices)
    subject_id = models.IntegerField()
    subject_label = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN)
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=32, blank=True)
    risk_reasons = models.JSONField(default=list, blank=True)
    verification_snapshot = models.JSONField(default=dict, blank=True)
    duplicate_signals = models.JSONField(default=list, blank=True)
    document_metadata = models.JSONField(default=list, blank=True)
    evidence_snapshot = models.JSONField(default=dict, blank=True)
    previous_subject_status = models.CharField(max_length=64, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "moderation_manual_review_case"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["status", "subject_type"]),
            models.Index(fields=["subject_type", "subject_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["subject_type", "subject_id"],
                condition=models.Q(status="open"),
                name="one_open_manual_review_case",
            )
        ]


class ReviewDecision(models.Model):
    case = models.ForeignKey(ManualReviewCase, related_name="decisions", on_delete=models.CASCADE)
    action = models.CharField(max_length=32)
    moderator_id = models.IntegerField()
    moderator_name = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    evidence_reviewed = models.JSONField(default=list, blank=True)
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "moderation_review_decision"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "idempotency_key"],
                name="unique_review_decision_key",
            )
        ]


from .comment_models import ModerationComment, ModerationCommentEdit  # noqa: E402,F401
from .report_models import ReportAttachment, UserReport  # noqa: E402,F401

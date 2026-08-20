from django.db import models

from ekomek_common.reports import ReportCategory, ReportStatus


class UserReport(models.Model):
    card_id = models.IntegerField(db_index=True)
    reporter_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    reporter_key = models.CharField(max_length=128, db_index=True)
    category = models.CharField(max_length=32, choices=ReportCategory.CHOICES)
    description = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=[(item, item) for item in ReportStatus.ALL],
        default=ReportStatus.PENDING,
    )
    reviewed_by = models.IntegerField(null=True, blank=True)
    reviewed_by_name = models.CharField(max_length=255, blank=True)
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "moderation_user_report"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["card_id", "reporter_key"]),
        ]


class ReportAttachment(models.Model):
    report = models.ForeignKey(UserReport, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="reports/attachments/")
    file_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "moderation_report_attachment"
        ordering = ["created_at", "id"]

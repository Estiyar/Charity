from django.db import models


class Notification(models.Model):
    class DeliveryChannel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        PUSH = "push", "Push"

    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    notification_type = models.CharField(max_length=128, db_index=True)
    event_type = models.CharField(max_length=128, blank=True)
    payload = models.JSONField(default=dict)
    deep_link = models.CharField(max_length=255, blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]


class NotificationDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RETRYING = "retrying", "Retrying"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    notification = models.ForeignKey(
        Notification,
        related_name="deliveries",
        on_delete=models.CASCADE,
    )
    channel = models.CharField(max_length=16, choices=Notification.DeliveryChannel.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    destination = models.CharField(max_length=255, blank=True)
    provider = models.CharField(max_length=64, blank=True)
    provider_message_id = models.CharField(max_length=128, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_delivery"
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("notification", "channel"),
                name="notifications_delivery_channel_unique",
            )
        ]


class NotificationDeliveryLog(models.Model):
    delivery = models.ForeignKey(
        NotificationDelivery,
        related_name="logs",
        on_delete=models.CASCADE,
    )
    attempt_number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=NotificationDelivery.Status.choices)
    response_payload = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_delivery_log"
        ordering = ["-created_at", "-id"]

from rest_framework import serializers

from .models import Notification, NotificationDelivery, NotificationDeliveryLog


class NotificationDeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDeliveryLog
        fields = ("id", "attempt_number", "status", "response_payload", "error_message", "created_at")
        read_only_fields = fields


class NotificationDeliverySerializer(serializers.ModelSerializer):
    logs = NotificationDeliveryLogSerializer(many=True, read_only=True)

    class Meta:
        model = NotificationDelivery
        fields = (
            "id",
            "channel",
            "status",
            "destination",
            "provider",
            "provider_message_id",
            "attempt_count",
            "last_error",
            "last_attempt_at",
            "next_attempt_at",
            "sent_at",
            "delivered_at",
            "logs",
        )
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="notification_type", read_only=True)
    recipient = serializers.IntegerField(source="recipient_id", read_only=True)
    deliveries = NotificationDeliverySerializer(many=True, read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "event_type",
            "title",
            "body",
            "payload",
            "deep_link",
            "recipient",
            "is_read",
            "created_at",
            "read_at",
            "deliveries",
        )
        read_only_fields = fields

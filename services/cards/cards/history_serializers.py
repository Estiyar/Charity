from rest_framework import serializers

from .models import CardHistoryEvent


class PublicHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CardHistoryEvent
        fields = ("id", "event_type", "summary", "created_at")
        read_only_fields = fields


class StaffHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CardHistoryEvent
        fields = (
            "id",
            "event_type",
            "summary",
            "public",
            "payload",
            "actor_id",
            "actor_role",
            "created_at",
        )
        read_only_fields = fields

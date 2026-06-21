from rest_framework import serializers

from apps.cards.models import FundraisingCard
from apps.cards.serializers import CardPrivateSerializer
from apps.documents.serializers import DocumentSerializer

from .models import ModerationLog


class ModerationLogSerializer(serializers.ModelSerializer):
    moderator_name = serializers.CharField(source="moderator.full_name", read_only=True)

    class Meta:
        model = ModerationLog
        fields = ("id", "action", "comment", "moderator_name", "created_at")
        read_only_fields = fields


class ModerationCardListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    documents_count = serializers.IntegerField(source="documents.count", read_only=True)

    class Meta:
        model = FundraisingCard
        fields = (
            "id",
            "full_name",
            "diagnosis",
            "city",
            "status",
            "author_name",
            "target_amount",
            "end_date",
            "documents_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ModerationCardDetailSerializer(CardPrivateSerializer):
    documents = DocumentSerializer(many=True, read_only=True)
    moderation_logs = ModerationLogSerializer(many=True, read_only=True)

    class Meta(CardPrivateSerializer.Meta):
        fields = CardPrivateSerializer.Meta.fields + ("documents", "moderation_logs")


class ModerationCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_comment(self, value):
        if self.context.get("comment_required") and not value.strip():
            raise serializers.ValidationError("Комментарий обязателен.")
        return value.strip()

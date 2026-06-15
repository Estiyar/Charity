from rest_framework import serializers

from apps.cards.models import FundraisingCard
from apps.cards.serializers import CardPrivateSerializer
from apps.documents.serializers import DocumentSerializer

from .models import ModerationLog, RedistributionDecision


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


class RedistributionDecisionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    target_card_name = serializers.CharField(source="target_card.full_name", read_only=True)
    decision_type_label = serializers.CharField(source="get_decision_type_display", read_only=True)

    class Meta:
        model = RedistributionDecision
        fields = (
            "id",
            "decision_type",
            "decision_type_label",
            "target_card",
            "target_card_name",
            "comment",
            "created_by_name",
            "created_at",
        )
        read_only_fields = fields


class RedistributionCreateSerializer(serializers.Serializer):
    decision_type = serializers.ChoiceField(choices=RedistributionDecision.DecisionType.choices)
    target_card_id = serializers.IntegerField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_target_card_id(self, value):
        if value is None:
            return value
        try:
            return FundraisingCard.objects.get(pk=value)
        except FundraisingCard.DoesNotExist as exc:
            raise serializers.ValidationError("Целевая карточка не найдена.") from exc


class RedistributionCardSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    redistribution_case = serializers.SerializerMethodField()
    escrow_balance = serializers.ReadOnlyField()

    class Meta:
        model = FundraisingCard
        fields = (
            "id",
            "full_name",
            "status",
            "author_name",
            "collected_amount",
            "escrow_balance",
            "escrow_available",
            "redistribution_case",
        )
        read_only_fields = fields

    def get_redistribution_case(self, obj):
        from .redistribution import get_redistribution_case

        return get_redistribution_case(obj)

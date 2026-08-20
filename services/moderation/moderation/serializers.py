from rest_framework import serializers

from .models import ManualReviewCase, ModerationLog, ReviewDecision
from .review_policy import allowed_actions


class ModerationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModerationLog
        fields = ("id", "action", "comment", "moderator_name", "created_at")
        read_only_fields = fields


class AdminModerationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModerationLog
        fields = ("id", "card_id", "card_name", "action", "comment", "moderator_name", "created_at")
        read_only_fields = fields


class ModerationCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    revision_comment = serializers.CharField(required=False, allow_blank=True, default="")
    internal_comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        from ekomek_common.comments import resolve_revision_comment

        revision, internal = resolve_revision_comment(attrs)
        if self.context.get("comment_required") and not revision:
            raise serializers.ValidationError({"revision_comment": "Комментарий для автора обязателен."})
        attrs["revision_comment"] = revision
        attrs["internal_comment"] = internal
        attrs["comment"] = revision
        return attrs


class ReviewDecisionInputSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    revision_comment = serializers.CharField(required=False, allow_blank=True, default="")
    internal_comment = serializers.CharField(required=False, allow_blank=True, default="")
    evidence_reviewed = serializers.ListField(child=serializers.CharField(), required=False)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        from ekomek_common.comments import resolve_revision_comment

        revision, internal = resolve_revision_comment(attrs)
        attrs["revision_comment"] = revision
        attrs["internal_comment"] = internal
        attrs["comment"] = revision
        return attrs


class ReviewDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewDecision
        fields = (
            "id",
            "action",
            "moderator_id",
            "moderator_name",
            "comment",
            "evidence_reviewed",
            "created_at",
        )
        read_only_fields = fields


class ManualReviewCaseListSerializer(serializers.ModelSerializer):
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = ManualReviewCase
        fields = (
            "id",
            "subject_type",
            "subject_id",
            "subject_label",
            "status",
            "risk_score",
            "risk_level",
            "risk_reasons",
            "opened_at",
            "updated_at",
            "allowed_actions",
        )
        read_only_fields = fields

    def get_allowed_actions(self, obj):
        return allowed_actions(obj)


class ManualReviewCaseDetailSerializer(ManualReviewCaseListSerializer):
    decisions = ReviewDecisionSerializer(many=True, read_only=True)
    moderation_logs = serializers.SerializerMethodField()
    audit_history = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta(ManualReviewCaseListSerializer.Meta):
        fields = ManualReviewCaseListSerializer.Meta.fields + (
            "verification_snapshot",
            "duplicate_signals",
            "document_metadata",
            "evidence_snapshot",
            "previous_subject_status",
            "decisions",
            "moderation_logs",
            "audit_history",
            "comments",
        )

    def get_moderation_logs(self, obj):
        if obj.subject_type != ManualReviewCase.SubjectType.CARD:
            return []
        logs = ModerationLog.objects.filter(card_id=obj.subject_id)
        return ModerationLogSerializer(logs, many=True).data

    def get_audit_history(self, obj):
        return ReviewDecisionSerializer(obj.decisions.all(), many=True).data

    def get_comments(self, obj):
        from .comment_services import list_moderation_comments

        request = self.context.get("request")
        user = getattr(request, "user", None)
        return list_moderation_comments("review", obj.id, user=user, include_internal=True)

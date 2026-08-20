from rest_framework import serializers

from ekomek_common.reports import ReportCategory, ReportStatus

from .report_models import ReportAttachment, UserReport


class ReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAttachment
        fields = ("id", "file", "file_name", "created_at")
        read_only_fields = fields


class UserReportSerializer(serializers.ModelSerializer):
    attachments = ReportAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = UserReport
        fields = (
            "id",
            "card_id",
            "reporter_user_id",
            "category",
            "description",
            "status",
            "reviewed_by",
            "reviewed_by_name",
            "resolution",
            "attachments",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReportCreateSerializer(serializers.Serializer):
    card_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=ReportCategory.CHOICES)
    description = serializers.CharField(min_length=10, max_length=5000)
    reporter_fingerprint = serializers.CharField(required=False, allow_blank=True, max_length=240)


class ReportResolveSerializer(serializers.Serializer):
    resolution = serializers.CharField(min_length=3, max_length=5000)
    status = serializers.ChoiceField(choices=[ReportStatus.RESOLVED, ReportStatus.DISMISSED])

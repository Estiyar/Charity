from rest_framework import serializers

from .models import City, Diagnosis, PlatformSettings, RiskConfig, RiskConfigAudit


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name")


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ("id", "name")


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = (
            "site_name",
            "demo_payment_enabled",
            "bank_integration_stub",
            "escrow_integration_stub",
            "pdf_auto_check_stub",
            "notifications_stub",
            "egov_integration_stub",
            "refund_commission_percent",
            "refund_deadline_days",
            "updated_at",
        )


class RiskConfigSerializer(serializers.ModelSerializer):
    audit_entries = serializers.SerializerMethodField()

    class Meta:
        model = RiskConfig
        fields = (
            "id",
            "version",
            "factor_weights",
            "risk_thresholds",
            "business_limits",
            "active",
            "created_by",
            "created_by_name",
            "created_at",
            "audit_entries",
        )
        read_only_fields = ("id", "created_at", "audit_entries")

    def get_audit_entries(self, obj):
        entries = obj.audit_entries.order_by("-created_at")[:20]
        return [
            {
                "id": entry.id,
                "actor_name": entry.actor_name,
                "action": entry.action,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]


class RiskConfigUpdateSerializer(serializers.Serializer):
    factor_weights = serializers.JSONField(required=False)
    risk_thresholds = serializers.JSONField(required=False)
    business_limits = serializers.JSONField(required=False)

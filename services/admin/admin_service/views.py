from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsAdmin

from .models import AdminAuditEvent, City, Diagnosis, PlatformSettings, RiskConfig, RiskConfigAudit
from .serializers import (
    CitySerializer,
    DiagnosisSerializer,
    PlatformSettingsSerializer,
    RiskConfigSerializer,
    RiskConfigUpdateSerializer,
)


class AdminCityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = CitySerializer
    pagination_class = None
    queryset = City.objects.order_by("name")


class AdminCityDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = City.objects.all()


class AdminDiagnosisListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = DiagnosisSerializer
    pagination_class = None
    queryset = Diagnosis.objects.order_by("name")


class AdminDiagnosisDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = Diagnosis.objects.all()


class AdminSettingsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.get_solo()).data)

    def patch(self, request):
        settings = PlatformSettings.get_solo()
        serializer = PlatformSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class InternalSettingsView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request):
        settings = PlatformSettings.get_solo()
        return Response(
            {
                "refund_commission_percent": settings.refund_commission_percent,
                "refund_deadline_days": settings.refund_deadline_days,
                "demo_payment_enabled": settings.demo_payment_enabled,
            }
        )


class AdminRiskConfigView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        config = RiskConfig.get_active()
        return Response(RiskConfigSerializer(config).data)

    def patch(self, request):
        config = RiskConfig.get_active()
        serializer = RiskConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_snapshot = {
            "factor_weights": dict(config.factor_weights),
            "risk_thresholds": dict(config.risk_thresholds),
            "business_limits": dict(config.business_limits),
        }
        changed = False
        if "factor_weights" in serializer.validated_data:
            config.factor_weights = serializer.validated_data["factor_weights"]
            changed = True
        if "risk_thresholds" in serializer.validated_data:
            config.risk_thresholds = serializer.validated_data["risk_thresholds"]
            changed = True
        if "business_limits" in serializer.validated_data:
            config.business_limits = serializer.validated_data["business_limits"]
            changed = True
        if changed:
            config.created_by = getattr(request.user, "id", None)
            config.created_by_name = getattr(request.user, "full_name", "") or ""
            config.save()
            new_snapshot = {
                "factor_weights": dict(config.factor_weights),
                "risk_thresholds": dict(config.risk_thresholds),
                "business_limits": dict(config.business_limits),
            }
            RiskConfigAudit.objects.create(
                config=config,
                actor_id=getattr(request.user, "id", None),
                actor_name=getattr(request.user, "full_name", "") or "",
                action="risk_config_updated",
                previous_snapshot=previous_snapshot,
                new_snapshot=new_snapshot,
            )
            AdminAuditEvent.objects.create(
                actor_id=getattr(request.user, "id", None),
                action="risk_config_updated",
                payload=new_snapshot,
            )
        return Response(RiskConfigSerializer(config).data)


class AdminRiskConfigHistoryView(generics.ListAPIView):
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        entries = RiskConfigAudit.objects.order_by("-created_at")[:50]
        data = [
            {
                "id": entry.id,
                "config_id": entry.config_id,
                "actor_name": entry.actor_name,
                "action": entry.action,
                "previous_snapshot": entry.previous_snapshot,
                "new_snapshot": entry.new_snapshot,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]
        return Response(data)


class InternalRiskConfigView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request):
        config = RiskConfig.get_active()
        return Response({
            "version": config.version,
            "factor_weights": config.get_weights(),
            "risk_thresholds": config.get_thresholds(),
            "business_limits": config.get_limits(),
        })

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsModeratorOrAdmin

from .models import FundraisingCard
from .risk_engine import calculate_risk_score, override_risk
from .risk_models import RiskAssessment, RiskOverride


class CardRiskAssessmentView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        assessment = RiskAssessment.latest_for_card(pk)
        if assessment is None:
            assessment = calculate_risk_score(card)
        overrides = RiskOverride.objects.filter(card_id=pk).order_by("-created_at")[:10]
        return Response({
            "card_id": pk,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "factors": assessment.factors,
            "config_version": assessment.config_version,
            "calculated_at": assessment.calculated_at.isoformat(),
            "overrides": [
                {
                    "id": o.id,
                    "moderator_name": o.moderator_name,
                    "previous_score": o.previous_score,
                    "new_score": o.new_score,
                    "new_level": o.new_level,
                    "reason": o.reason,
                    "created_at": o.created_at.isoformat(),
                }
                for o in overrides
            ],
        })


class CardRiskRecalculateView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        assessment = calculate_risk_score(card)
        return Response({
            "card_id": pk,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "factors": assessment.factors,
        })


class CardRiskOverrideView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        new_score = request.data.get("risk_score")
        reason = (request.data.get("reason") or "").strip()
        if new_score is None or not reason:
            return Response(
                {"detail": "Требуется risk_score и reason."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            new_score = int(new_score)
        except (TypeError, ValueError):
            return Response({"detail": "risk_score должен быть числом."}, status=status.HTTP_400_BAD_REQUEST)
        if not (0 <= new_score <= 100):
            return Response({"detail": "risk_score должен быть 0–100."}, status=status.HTTP_400_BAD_REQUEST)
        override = override_risk(pk, request.user, new_score, reason)
        return Response({
            "card_id": pk,
            "previous_score": override.previous_score,
            "new_score": override.new_score,
            "new_level": override.new_level,
            "reason": override.reason,
        })


class InternalCardRiskView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        assessment = RiskAssessment.latest_for_card(pk)
        if assessment is None:
            return Response({"risk_score": 0, "risk_level": "low", "factors": []})
        return Response({
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "factors": assessment.factors,
            "config_version": assessment.config_version,
        })

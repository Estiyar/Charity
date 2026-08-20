from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsModeratorOrAdmin
from ekomek_common.constants import VIEWABLE_PUBLIC_STATUSES
from ekomek_common.http import ServiceClientError, moderation_client
from ekomek_common.reports import request_reporter_fingerprint

from .models import FundraisingCard
from .serializers import CardStaffSerializer, InternalCardSerializer
from .suspend_services import SuspendActionError, suspend_card, unsuspend_card, update_report_risk
from .views import CardAccessMixin


class CardReportCreateView(CardAccessMixin, APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None or card.status not in VIEWABLE_PUBLIC_STATUSES:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = {
            "card_id": card.id,
            "category": request.data.get("category"),
            "description": request.data.get("description", ""),
            "reporter_fingerprint": request_reporter_fingerprint(request),
        }
        files = {}
        for key, uploaded in request.FILES.items():
            files[key] = uploaded
        try:
            client = moderation_client()
            multipart = {key: (uploaded.name, uploaded.read(), uploaded.content_type) for key, uploaded in files.items()}
            response = client.post(
                "/internal/reports/",
                data=payload,
                files=multipart or None,
            )
        except ServiceClientError as exc:
            detail = (exc.payload or {}).get("detail") or str(exc)
            return Response({"detail": detail}, status=exc.status_code or status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_201_CREATED)


class CardSuspendView(CardAccessMixin, APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        reason = (request.data.get("reason") or "").strip()
        try:
            suspend_card(card, reason, actor=request.user, source="moderator")
        except SuspendActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CardStaffSerializer(card, context={"request": request}).data)


class CardUnsuspendView(CardAccessMixin, APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        reason = (request.data.get("reason") or "").strip()
        try:
            unsuspend_card(card, reason, actor=request.user)
        except SuspendActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CardStaffSerializer(card, context={"request": request}).data)


class InternalSuspendView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        reason = (request.data.get("reason") or "").strip()
        source = (request.data.get("source") or "internal").strip()
        try:
            suspend_card(card, reason, source=source)
        except SuspendActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InternalCardSerializer(card).data)


class InternalUnsuspendView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        reason = (request.data.get("reason") or "").strip()
        try:
            unsuspend_card(card, reason)
        except SuspendActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InternalCardSerializer(card).data)


class InternalReportRiskView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        update_report_risk(
            card,
            int(request.data.get("report_risk_score") or 0),
            int(request.data.get("unique_report_count") or 0),
        )
        return Response(InternalCardSerializer(card).data)

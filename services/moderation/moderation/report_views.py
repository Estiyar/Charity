from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsModeratorOrAdmin

from .report_models import ReportAttachment, UserReport
from .report_serializers import ReportCreateSerializer, ReportResolveSerializer, UserReportSerializer
from .report_services import ReportActionError, create_user_report, open_reports, resolve_user_report


class InternalReportCreateView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachments = list(request.FILES.values())
        try:
            report = create_user_report(
                card_id=serializer.validated_data["card_id"],
                category=serializer.validated_data["category"],
                description=serializer.validated_data["description"],
                request=request,
                attachments=attachments,
            )
        except ReportActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ModerationReportListView(generics.ListAPIView):
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = UserReportSerializer

    def get_queryset(self):
        queryset = open_reports()
        card_id = self.request.query_params.get("card_id")
        if card_id:
            queryset = UserReport.objects.filter(card_id=card_id).order_by("-created_at")
        return queryset


class ModerationReportDetailView(generics.RetrieveAPIView):
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = UserReportSerializer
    queryset = UserReport.objects.all()


class ModerationReportResolveView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        serializer = ReportResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            report = resolve_user_report(
                pk,
                request.user,
                resolution=serializer.validated_data["resolution"],
                status=serializer.validated_data["status"],
            )
        except UserReport.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except ReportActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserReportSerializer(report).data)

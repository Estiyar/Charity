from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import IsModeratorOrAdmin

from .models import ManualReviewCase
from .review_actions import apply_review_decision
from .review_policy import COMMENT_REQUIRED_ACTIONS
from .serializers import (
    ManualReviewCaseDetailSerializer,
    ManualReviewCaseListSerializer,
    ReviewDecisionInputSerializer,
)
from .services import ModerationActionError


class ManualReviewListView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):
        queryset = ManualReviewCase.objects.all()
        subject_type = request.query_params.get("subject_type")
        status_filter = request.query_params.get("status", ManualReviewCase.Status.OPEN)
        if subject_type:
            queryset = queryset.filter(subject_type=subject_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response(ManualReviewCaseListSerializer(queryset, many=True).data)


class ManualReviewDetailView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request, pk):
        case = ManualReviewCase.objects.filter(pk=pk).first()
        if case is None:
            return Response({"detail": "Not found."}, status=404)
        return Response(ManualReviewCaseDetailSerializer(case).data)


class ManualReviewActionView(APIView):
    permission_classes = [IsModeratorOrAdmin]
    action_name = ""

    def post(self, request, pk):
        case = ManualReviewCase.objects.filter(pk=pk).first()
        if case is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = ReviewDecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment", "")
        internal_comment = serializer.validated_data.get("internal_comment") or ""
        if self.action_name in COMMENT_REQUIRED_ACTIONS and not comment:
            return Response({"revision_comment": ["Комментарий обязателен."]}, status=400)
        try:
            case = apply_review_decision(
                case.id,
                self.action_name,
                request.user,
                comment=comment,
                evidence_reviewed=serializer.validated_data.get("evidence_reviewed"),
                idempotency_key=serializer.validated_data.get("idempotency_key") or "",
                internal_comment=internal_comment,
            )
        except ManualReviewCase.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        except ModerationActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ManualReviewCaseDetailSerializer(case).data)


class ManualReviewApproveView(ManualReviewActionView):
    action_name = "approve"


class ManualReviewRejectView(ManualReviewActionView):
    action_name = "reject"


class ManualReviewRequestRevisionView(ManualReviewActionView):
    action_name = "request_revision"


class ManualReviewSuspendView(ManualReviewActionView):
    action_name = "suspend"


class ManualReviewUnsuspendView(ManualReviewActionView):
    action_name = "unsuspend"

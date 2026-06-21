from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus
from apps.documents.models import Document, DocumentStatus
from apps.documents.serializers import DocumentSerializer
from apps.users.permissions import IsModerator

from .serializers import (
    ModerationCardDetailSerializer,
    ModerationCardListSerializer,
    ModerationCommentSerializer,
)
from .services import (
    ModerationActionError,
    approve_card,
    reject_card,
    request_card_revision,
)

MODERATION_STATUSES = {
    CardStatus.PENDING_MODERATION,
    CardStatus.REVISION_REQUIRED,
    CardStatus.APPROVED,
    CardStatus.ACTIVE,
    CardStatus.REJECTED,
}


class ModerationCardListView(generics.ListAPIView):
    permission_classes = [IsModerator]
    serializer_class = ModerationCardListSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = FundraisingCard.objects.select_related("author").prefetch_related(
            "documents"
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            return queryset.filter(status=status_filter).order_by("-updated_at")
        return queryset.filter(status__in=MODERATION_STATUSES).order_by("-updated_at")


class ModerationCardDetailView(generics.RetrieveAPIView):
    permission_classes = [IsModerator]
    serializer_class = ModerationCardDetailSerializer
    queryset = FundraisingCard.objects.select_related("author").prefetch_related(
        "documents",
        "moderation_logs__moderator",
    )


class ModerationDocumentListView(generics.ListAPIView):
    permission_classes = [IsModerator]
    serializer_class = DocumentSerializer
    pagination_class = None

    def get_queryset(self):
        return Document.objects.filter(
            status__in=[DocumentStatus.UPLOADED, DocumentStatus.UNDER_REVIEW]
        ).select_related("card").order_by("-created_at")


class ModerationActionView(APIView):
    permission_classes = [IsModerator]
    action_name = ""
    comment_required = False

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        serializer = ModerationCommentSerializer(
            data=request.data,
            context={"comment_required": self.comment_required},
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment", "")
        try:
            card = self.perform_action(card, request.user, comment)
        except ModerationActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            ModerationCardDetailSerializer(card, context={"request": request}).data
        )

    def perform_action(self, card, moderator, comment):
        raise NotImplementedError


class ModerationApproveView(ModerationActionView):
    action_name = "approve"

    def perform_action(self, card, moderator, comment):
        return approve_card(card, moderator, comment)


class ModerationRejectView(ModerationActionView):
    action_name = "reject"
    comment_required = True

    def perform_action(self, card, moderator, comment):
        return reject_card(card, moderator, comment)


class ModerationRequestRevisionView(ModerationActionView):
    action_name = "request_revision"
    comment_required = True

    def perform_action(self, card, moderator, comment):
        return request_card_revision(card, moderator, comment)

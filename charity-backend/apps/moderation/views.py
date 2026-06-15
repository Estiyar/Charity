from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import FundraisingCard
from apps.cards.views import CardAccessMixin
from apps.common.card_status import CardStatus
from apps.documents.models import Document, DocumentStatus
from apps.documents.serializers import DocumentSerializer
from apps.users.models import Role
from apps.users.permissions import IsModerator, IsModeratorOrAdmin

from .redistribution import (
    RedistributionError,
    create_redistribution_decision,
    get_eligible_redistribution_cards,
    get_redistribution_case,
)
from .serializers import (
    ModerationCardDetailSerializer,
    ModerationCardListSerializer,
    ModerationCommentSerializer,
    RedistributionCardSerializer,
    RedistributionCreateSerializer,
    RedistributionDecisionSerializer,
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


class CardRedistributionView(CardAccessMixin, APIView):
    permission_classes = [AllowAny]

    def get_card(self, pk):
        card = get_object_or_404(FundraisingCard.objects.select_related("author"), pk=pk)
        if card.is_public or self.can_see_private_data(card):
            return card
        raise Http404

    def get(self, request, pk):
        card = self.get_card(pk)
        decisions = card.redistributions.select_related(
            "target_card", "created_by"
        ).order_by("-created_at")
        return Response(
            {
                "case": get_redistribution_case(card),
                "eligible": card.status in {
                    CardStatus.ACTIVE,
                    CardStatus.COMPLETED,
                    CardStatus.DECEASED,
                    CardStatus.REDISTRIBUTION,
                },
                "decisions": RedistributionDecisionSerializer(decisions, many=True).data,
            }
        )

    def post(self, request, pk):
        if not request.user.is_authenticated or request.user.role not in (Role.MODERATOR, Role.ADMIN):
            return Response({"detail": "Нет доступа."}, status=status.HTTP_403_FORBIDDEN)
        card = self.get_card(pk)
        serializer = RedistributionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            decision = create_redistribution_decision(
                card=card,
                actor=request.user,
                decision_type=data["decision_type"],
                target_card=data.get("target_card_id"),
                comment=data.get("comment", ""),
            )
        except RedistributionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            RedistributionDecisionSerializer(decision).data,
            status=status.HTTP_201_CREATED,
        )


class ModerationRedistributionCardListView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):
        cards = get_eligible_redistribution_cards()
        return Response(RedistributionCardSerializer(cards, many=True).data)

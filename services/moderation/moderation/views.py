from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics

from ekomek_common.auth import IsAdmin, IsModeratorOrAdmin
from ekomek_common.constants import MODERATION_LIST_STATUSES

from .models import ModerationLog
from .serializers import AdminModerationLogSerializer, ModerationCommentSerializer, ModerationLogSerializer
from .services import (
    ModerationActionError,
    approve_card,
    fetch_card,
    fetch_documents,
    list_cards,
    reject_card,
    request_card_revision,
)


class ModerationCardListView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):
        status_filter = request.query_params.get("status")
        cards = list_cards(status_filter)
        if not status_filter:
            cards = [card for card in cards if card.get("status") in MODERATION_LIST_STATUSES]
        payload = []
        for card in cards:
            payload.append(
                {
                    "id": card["id"],
                    "full_name": card.get("full_name"),
                    "diagnosis": card.get("diagnosis"),
                    "city": card.get("city"),
                    "status": card.get("status"),
                    "author_name": card.get("author_full_name") or card.get("author_email"),
                    "target_amount": card.get("target_amount"),
                    "end_date": card.get("end_date"),
                    "documents_count": len(fetch_documents(card["id"])),
                    "needs_extra_review": card.get("needs_extra_review"),
                    "created_at": card.get("created_at"),
                    "updated_at": card.get("updated_at"),
                }
            )
        return Response(payload)


class ModerationCardDetailView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request, pk):
        card = fetch_card(pk, request.user)
        if card is None:
            return Response({"detail": "Not found."}, status=404)
        card["documents"] = fetch_documents(pk)
        card["moderation_logs"] = ModerationLogSerializer(
            ModerationLog.objects.filter(card_id=pk), many=True
        ).data
        return Response(card)


class ModerationActionView(APIView):
    permission_classes = [IsModeratorOrAdmin]
    comment_required = False

    def post(self, request, pk):
        card = fetch_card(pk)
        if card is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = ModerationCommentSerializer(
            data=request.data, context={"comment_required": self.comment_required}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            card = self.perform_action(card, request.user, data)
        except ModerationActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        card["documents"] = fetch_documents(pk)
        card["moderation_logs"] = ModerationLogSerializer(
            ModerationLog.objects.filter(card_id=pk), many=True
        ).data
        return Response(card)

    def perform_action(self, card, moderator, data):
        raise NotImplementedError


class ModerationApproveView(ModerationActionView):
    def perform_action(self, card, moderator, data):
        return approve_card(card, moderator, data.get("comment") or "")


class ModerationRejectView(ModerationActionView):
    comment_required = True

    def perform_action(self, card, moderator, data):
        return reject_card(card, moderator, data["comment"])


class ModerationRequestRevisionView(ModerationActionView):
    comment_required = True

    def perform_action(self, card, moderator, data):
        return request_card_revision(
            card,
            moderator,
            data["revision_comment"],
            data.get("internal_comment") or "",
        )


class AdminModerationLogListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminModerationLogSerializer
    pagination_class = None
    queryset = ModerationLog.objects.order_by("-created_at")

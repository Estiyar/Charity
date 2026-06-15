from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import FundraisingCard
from apps.cards.serializers import EDITABLE_STATUSES
from apps.cards.views import CardAccessMixin
from rest_framework.permissions import AllowAny

from apps.users.permissions import IsAuthor, IsModerator

from .models import Document, DocumentStatus
from .serializers import DocumentModerationSerializer, DocumentSerializer


class CardDocumentListCreateView(CardAccessMixin, generics.ListCreateAPIView):
    pagination_class = None
    serializer_class = DocumentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthor()]
        return [AllowAny()]

    def get_card(self):
        card = get_object_or_404(
            FundraisingCard.objects.select_related("author"),
            pk=self.kwargs["pk"],
        )
        if card.is_public or self.can_see_private_data(card):
            return card
        raise Http404

    def get_queryset(self):
        return Document.objects.filter(card_id=self.kwargs["pk"]).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        card = self.get_card()
        if not self.can_see_private_data(card):
            return Response(
                {"detail": "Нет доступа к документам."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        card = self.get_card()
        if card.author_id != request.user.id:
            raise Http404
        if card.status not in EDITABLE_STATUSES:
            return Response(
                {"detail": "Загружать документы можно только для редактируемой карточки."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = DocumentSerializer(
            data=request.data,
            context={"request": request, "card": card},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(
            DocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentVerifyView(APIView):
    permission_classes = [IsModerator]

    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        serializer = DocumentModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        document.status = DocumentStatus.VERIFIED
        if "has_confidential" in data:
            document.has_confidential = data["has_confidential"]
        if data.get("comment"):
            document.moderator_comment = data["comment"]
        document.save()
        return Response(DocumentSerializer(document).data)


class DocumentRejectView(APIView):
    permission_classes = [IsModerator]

    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        serializer = DocumentModerationSerializer(
            data=request.data,
            context={"comment_required": True},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        document.status = DocumentStatus.REJECTED
        document.moderator_comment = data["comment"]
        if "has_confidential" in data:
            document.has_confidential = data["has_confidential"]
        document.save()
        return Response(DocumentSerializer(document).data)

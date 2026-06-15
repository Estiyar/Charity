from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.card_status import CardStatus, InvalidStatusTransition, PUBLIC_STATUSES, transition
from apps.users.models import Role
from apps.users.permissions import IsAuthor

from .filters import CardFilter
from .models import FundraisingCard
from .permissions import CanManageCard, IsAuthorRole
from .serializers import (
    EDITABLE_STATUSES,
    CardPrivateSerializer,
    CardPublicSerializer,
    CardWriteSerializer,
)


class CardAccessMixin:
    def can_see_private_data(self, card):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.role in (Role.MODERATOR, Role.ADMIN):
            return True
        if user.role == Role.AUTHOR and card.author_id == user.id:
            return True
        return False

    def get_queryset(self):
        queryset = FundraisingCard.objects.select_related("author")
        user = self.request.user
        if not user.is_authenticated:
            return queryset.filter(status__in=PUBLIC_STATUSES)
        if user.role in (Role.MODERATOR, Role.ADMIN):
            return queryset
        if user.role == Role.AUTHOR:
            return queryset.filter(
                Q(status__in=PUBLIC_STATUSES) | Q(author=user)
            )
        return queryset.filter(status__in=PUBLIC_STATUSES)

    def get_card_serializer(self, card):
        if self.can_see_private_data(card):
            return CardPrivateSerializer(card, context=self.get_serializer_context())
        return CardPublicSerializer(card, context=self.get_serializer_context())

    def get_visible_card(self, pk):
        card = get_object_or_404(FundraisingCard.objects.select_related("author"), pk=pk)
        if card.is_public or self.can_see_private_data(card):
            return card
        raise Http404


class MyCardsListView(generics.ListAPIView):
    permission_classes = [IsAuthor]
    serializer_class = CardPrivateSerializer
    pagination_class = None

    def get_queryset(self):
        return FundraisingCard.objects.filter(
            author=self.request.user
        ).select_related("author").order_by("-created_at")


class CardListCreateView(CardAccessMixin, generics.ListCreateAPIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_class = CardFilter
    search_fields = ("full_name", "diagnosis", "description", "city")
    ordering_fields = ("created_at", "end_date", "target_amount", "collected_amount")

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthorRole()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CardWriteSerializer
        return CardPublicSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        cards = page if page is not None else queryset
        data = [self.get_card_serializer(card).data for card in cards]
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)

    def create(self, request, *args, **kwargs):
        serializer = CardWriteSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        card = serializer.save()
        return Response(
            CardPrivateSerializer(card, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class CardDetailView(CardAccessMixin, generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [CanManageCard()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return CardWriteSerializer
        return CardPublicSerializer

    def get_object(self):
        return self.get_visible_card(self.kwargs["pk"])

    def retrieve(self, request, *args, **kwargs):
        card = self.get_object()
        serializer = self.get_card_serializer(card)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        card = self.get_object()
        if card.author_id != request.user.id:
            raise Http404
        if card.status not in EDITABLE_STATUSES:
            return Response(
                {"detail": "Редактировать можно только черновик или карточку на доработке."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CardWriteSerializer(
            card,
            data=request.data,
            partial=kwargs.get("partial", False),
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        card = serializer.save()
        return Response(
            CardPrivateSerializer(card, context=self.get_serializer_context()).data
        )

    def destroy(self, request, *args, **kwargs):
        card = self.get_object()
        if card.author_id != request.user.id:
            raise Http404
        if card.status != CardStatus.DRAFT:
            return Response(
                {"detail": "Удалить можно только черновик."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        card.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CardSubmitView(CardAccessMixin, APIView):
    permission_classes = [CanManageCard]

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk, author=request.user)
        try:
            transition(card, CardStatus.PENDING_MODERATION)
        except InvalidStatusTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            CardPrivateSerializer(card, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

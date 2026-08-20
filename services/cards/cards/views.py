from django.utils import timezone
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsAdmin, IsAuthor, IsModeratorOrAdmin
from ekomek_common.constants import (
    EDITABLE_CARD_STATUSES,
    PUBLIC_CARD_STATUSES,
    CardStatus,
    InvalidStatusTransition,
    Role,
)
from ekomek_common.outbox import enqueue_event

from .duplicate_services import apply_duplicate_check, mark_duplicate_override
from .filters import CardFilter
from .models import FundraisingCard
from .permissions import CanManageCard
from .repositories import CardRepository
from .serializers import (
    AdminCardSerializer,
    AdminCardStatusSerializer,
    CardAuthorSerializer,
    CardPublicSerializer,
    CardStaffSerializer,
    CardWriteSerializer,
    InternalCardSerializer,
)
from .recipient_services import RecipientVerifyError, verify_recipient_for_author
from .services import (
    collect_amount,
    representation_allows_active,
    set_escrow_totals,
    submit_card_for_moderation,
    transition_card,
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
        return CardRepository().visible_qs(self.request.user)

    def get_card_serializer(self, card, *, reveal=False, include_trust=False):
        user = self.request.user
        context = {**self.get_serializer_context(), "include_trust": include_trust}
        if (
            reveal
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) in Role.STAFF
        ):
            return CardStaffSerializer(card, context=context)
        if self.can_see_private_data(card):
            return CardAuthorSerializer(card, context=context)
        return CardPublicSerializer(card, context=context)

    def get_visible_card(self, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        if card.is_publicly_viewable or self.can_see_private_data(card):
            return card
        raise Http404


class MyCardsListView(generics.ListAPIView):
    permission_classes = [IsAuthor]
    serializer_class = CardAuthorSerializer
    pagination_class = None

    def get_queryset(self):
        return CardRepository().for_author(self.request.user.id)


class CardListCreateView(CardAccessMixin, generics.ListCreateAPIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_class = CardFilter
    search_fields = ("full_name", "diagnosis", "description", "city")
    ordering_fields = ("created_at", "end_date", "target_amount", "collected_amount", "age")

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthor()]
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
        serializer = CardWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        card = serializer.save()
        return Response(
            CardAuthorSerializer(card, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class CardDetailView(CardAccessMixin, generics.RetrieveUpdateDestroyAPIView):
    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [CanManageCard()]
        return [AllowAny()]

    def get_object(self):
        return self.get_visible_card(self.kwargs["pk"])

    def retrieve(self, request, *args, **kwargs):
        return Response(self.get_card_serializer(self.get_object(), reveal=True, include_trust=True).data)

    def update(self, request, *args, **kwargs):
        card = self.get_object()
        if card.author_id != request.user.id:
            raise Http404
        if card.status not in EDITABLE_CARD_STATUSES | {CardStatus.ACTIVE}:
            return Response(
                {"detail": "Редактировать можно только черновик, карточку на доработке или активный сбор."},
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
        return Response(CardAuthorSerializer(card, context=self.get_serializer_context()).data)

    def destroy(self, request, *args, **kwargs):
        card = self.get_object()
        if card.author_id != request.user.id:
            raise Http404
        if card.status != CardStatus.DRAFT:
            return Response({"detail": "Удалить можно только черновик."}, status=400)
        card.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipientVerifyView(APIView):
    permission_classes = [IsAuthor]

    def post(self, request):
        try:
            payload = verify_recipient_for_author(request.user, request.data)
        except RecipientVerifyError as exc:
            body = {"detail": exc.message, "code": exc.code}
            body.update(exc.errors)
            return Response(body, status=exc.status_code)
        return Response(payload)


class CardSubmitView(APIView):
    permission_classes = [CanManageCard]

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk, author_id=request.user.id)
        try:
            submit_card_for_moderation(card, request=request)
        except InvalidStatusTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CardAuthorSerializer(card, context={"request": request}).data)


class AdminCardListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminCardSerializer
    pagination_class = None
    queryset = FundraisingCard.objects.order_by("-created_at")


class AdminCardSetStatusView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        serializer = AdminCardStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        old_status = card.status
        if new_status == CardStatus.ACTIVE and card.duplicate_suspected:
            mark_duplicate_override(card)
        if old_status != new_status:
            from .history_services import record_status_change

            card.status = new_status
            update_fields = ["status", "updated_at"]
            if new_status == CardStatus.ACTIVE:
                card.moderation_verified_at = timezone.now()
                update_fields.append("moderation_verified_at")
            card.save(update_fields=update_fields)
            record_status_change(card, old_status, new_status, actor=request.user)
            enqueue_event(
                "card.status_changed",
                "card",
                card.id,
                {"card_id": card.id, "status": new_status, "previous_status": old_status},
            )
        return Response(AdminCardSerializer(card).data)


class InternalCardView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        card = FundraisingCard.objects.filter(pk=pk).first()
        if card is None:
            return Response({"detail": "Not found."}, status=404)
        serializer_class = (
            CardStaffSerializer if request.query_params.get("reveal") == "1" else InternalCardSerializer
        )
        return Response(serializer_class(card, context={"request": request}).data)


def _truthy_flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


class InternalCardListView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request):
        beneficiary_id = request.query_params.get("beneficiary_id")
        if beneficiary_id:
            cards = CardRepository().list_for_beneficiary(beneficiary_id)
            return Response(InternalCardSerializer(cards, many=True).data)
        status_filter = request.query_params.get("status")
        cards = CardRepository().list_by_status(status_filter)
        return Response(InternalCardSerializer(cards, many=True).data)


class InternalTransitionView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        target = request.data.get("status")
        from ekomek_common.comments import resolve_revision_comment

        revision_comment, _internal = resolve_revision_comment(request.data)
        comment = revision_comment or request.data.get("comment", "")
        if target == CardStatus.ACTIVE:
            if _truthy_flag(request.data.get("duplicate_override")):
                mark_duplicate_override(card)
            else:
                apply_duplicate_check(card)
            if card.duplicate_suspected and not card.duplicate_override:
                return Response(
                    {
                        "detail": "Карточка с признаками дубля не может быть опубликована без решения модератора."
                    },
                    status=400,
                )
        if target == CardStatus.ACTIVE and not representation_allows_active(card):
            return Response(
                {"detail": "Сбор для другого получателя нельзя активировать без подтверждённого представительства."},
                status=400,
            )
        try:
            if target == CardStatus.ACTIVE and card.status in (
                CardStatus.PENDING_MODERATION,
                CardStatus.MANUAL_REVIEW,
            ):
                transition_card(card, CardStatus.APPROVED, comment=comment)
                transition_card(card, CardStatus.ACTIVE, comment=comment)
            else:
                transition_card(card, target, comment=comment)
        except InvalidStatusTransition as exc:
            return Response({"detail": str(exc)}, status=400)
        if comment:
            card.moderator_comment = comment
            card.save(update_fields=["moderator_comment", "updated_at"])
        from .comment_services import apply_transition_comments

        apply_transition_comments(card, request.data)
        return Response(InternalCardSerializer(card).data)


class InternalCollectView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        amount = request.data.get("amount")
        idempotency_key = request.data.get("idempotency_key")
        card = collect_amount(pk, amount, idempotency_key=idempotency_key)
        return Response(InternalCardSerializer(card).data)


class InternalEscrowView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        set_escrow_totals(pk, request.data.get("spent", 0), request.data.get("pending", 0))
        card = FundraisingCard.objects.get(pk=pk)
        return Response(InternalCardSerializer(card).data)


class InternalPhotoView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        photo = request.data.get("photo_url")
        if photo:
            card.photo_url = photo
            card.save(update_fields=["photo_url", "updated_at"])
        return Response(InternalCardSerializer(card).data)

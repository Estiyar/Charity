from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import FundraisingCard
from apps.cards.views import CardAccessMixin
from apps.common.card_status import CardStatus
from apps.users.permissions import IsModerator

from .models import Expense, ExpenseStatus
from .serializers import (
    ExpenseCreateSerializer,
    ExpenseModerationSerializer,
    ExpenseSerializer,
    ModerationExpenseListSerializer,
)
from .services import (
    ExpenseActionError,
    approve_expense,
    reject_expense,
    request_expense_clarification,
)

EXPENSE_CARD_STATUSES = {CardStatus.ACTIVE, CardStatus.COMPLETED}


class CardExpenseListCreateView(CardAccessMixin, generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    pagination_class = None

    def get_card(self):
        card = get_object_or_404(
            FundraisingCard.objects.select_related("author"),
            pk=self.kwargs["pk"],
        )
        if card.is_public or self.can_see_private_data(card):
            return card
        raise Http404

    def get_queryset(self):
        card = self.get_card()
        queryset = Expense.objects.filter(card=card).order_by("-date", "-created_at")
        if not self.can_see_private_data(card):
            queryset = queryset.filter(status=ExpenseStatus.APPROVED)
        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def list(self, request, *args, **kwargs):
        self.get_card()
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        card = self.get_card()
        if not request.user.is_authenticated or card.author_id != request.user.id:
            raise Http404
        if card.status not in EXPENSE_CARD_STATUSES:
            return Response(
                {"detail": "Добавлять расходы можно только для активного или завершённого сбора."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ExpenseCreateSerializer(
            data=request.data,
            context={"request": request, "card": card},
        )
        serializer.is_valid(raise_exception=True)
        expense = serializer.save()
        return Response(
            ExpenseSerializer(expense, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ModerationExpenseListView(generics.ListAPIView):
    permission_classes = [IsModerator]
    serializer_class = ModerationExpenseListSerializer
    pagination_class = None

    def get_queryset(self):
        return Expense.objects.filter(status=ExpenseStatus.PENDING).select_related(
            "card"
        ).order_by("-created_at")


class ExpenseModerationActionView(APIView):
    permission_classes = [IsModerator]
    comment_required = False

    def post(self, request, pk):
        expense = get_object_or_404(Expense.objects.select_related("card"), pk=pk)
        serializer = ExpenseModerationSerializer(
            data=request.data,
            context={"comment_required": self.comment_required},
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment", "")
        try:
            expense = self.perform_action(expense, comment)
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExpenseSerializer(expense, context={"request": request}).data)

    def perform_action(self, expense, comment):
        raise NotImplementedError


class ExpenseApproveView(ExpenseModerationActionView):
    def perform_action(self, expense, comment):
        return approve_expense(expense, comment)


class ExpenseRejectView(ExpenseModerationActionView):
    comment_required = True

    def perform_action(self, expense, comment):
        return reject_expense(expense, comment)


class ExpenseRequestClarificationView(ExpenseModerationActionView):
    comment_required = True

    def perform_action(self, expense, comment):
        return request_expense_clarification(expense, comment)

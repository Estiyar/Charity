from django.http import FileResponse, Http404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import HasInternalToken, IsAdmin, IsAuthor, IsModerator
from ekomek_common.constants import EXPENSE_CARD_STATUSES, Role
from ekomek_common.audit import log_sensitive_access

from .money_totals import card_escrow_totals
from .models import Expense
from .reconcile import reconcile_card
from .reporting import card_is_public, public_report
from .repositories import ExpenseRepository
from .serializers import (
    AdminExpenseSerializer,
    ExpenseCreateSerializer,
    ExpenseDecisionSerializer,
    ExpenseModerationSerializer,
    ExpenseSerializer,
    ExpenseUpdateSerializer,
    ModerationExpenseListSerializer,
)
from .workflow import (
    ExpenseActionError,
    approve_expense,
    cancel_expense,
    fetch_card,
    mark_expense_paid,
    reject_expense,
    request_expense_revision,
    submit_expense,
)


def can_see_private(user, card):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.role in Role.STAFF:
        return True
    return user.role == Role.AUTHOR and card["author_id"] == user.id


def card_or_404(card_id, request, require_visible=True):
    card = fetch_card(card_id)
    if card is None:
        raise Http404
    if require_visible and not (card_is_public(card) or can_see_private(request.user, card)):
        raise Http404
    return card


class CardExpenseListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    pagination_class = None

    def get_card(self):
        return card_or_404(self.kwargs["pk"], self.request)

    def get_queryset(self):
        card = self.get_card()
        return ExpenseRepository().for_card(card["id"], public_only=not can_see_private(self.request.user, card))

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ExpenseCreateSerializer
        return ExpenseSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method != "POST":
            context["public"] = not can_see_private(self.request.user, self.get_card())
            context["include_internal"] = getattr(self.request.user, "role", None) in Role.STAFF
        return context

    def create(self, request, *args, **kwargs):
        card = self.get_card()
        if not request.user.is_authenticated or card["author_id"] != request.user.id:
            raise Http404
        if card["status"] not in EXPENSE_CARD_STATUSES:
            return Response(
                {"detail": "Добавлять расходы можно только для активного или завершённого сбора."},
                status=400,
            )
        serializer = ExpenseCreateSerializer(data=request.data, context={"request": request, "card": card})
        serializer.is_valid(raise_exception=True)
        try:
            expense = serializer.save()
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ExpenseSerializer(expense).data, status=201)


class CardPublicExpenseReportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        card = card_or_404(pk, request)
        if not card_is_public(card) and not can_see_private(request.user, card):
            raise Http404
        return Response(public_report(pk))


class ExpenseDetailView(APIView):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthor()]
        return [AllowAny()]

    def get(self, request, pk):
        expense = Expense.objects.filter(pk=pk).first()
        if expense is None:
            raise Http404
        card = card_or_404(expense.card_id, request)
        public = not can_see_private(request.user, card)
        if public:
            raise Http404
        include_internal = getattr(request.user, "role", None) in Role.STAFF
        data = ExpenseSerializer(
            expense,
            context={"request": request, "include_internal": include_internal},
        ).data
        data["decisions"] = ExpenseDecisionSerializer(expense.decisions.all(), many=True).data
        return Response(data)

    def patch(self, request, pk):
        from .edit_services import update_expense

        expense = Expense.objects.filter(pk=pk).first()
        if expense is None:
            raise Http404
        card = fetch_card(expense.card_id)
        if not card or card["author_id"] != request.user.id:
            raise Http404
        serializer = ExpenseUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data.pop("file", None)
        try:
            expense = update_expense(expense, serializer.validated_data, actor=request.user, uploaded=uploaded)
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ExpenseSerializer(expense, context={"request": request}).data)


class ExpenseSubmitView(APIView):
    permission_classes = [IsAuthor]

    def post(self, request, pk):
        return _author_action(request, pk, submit_expense)


class ExpenseCancelView(APIView):
    permission_classes = [IsAuthor]

    def post(self, request, pk):
        return _author_action(request, pk, cancel_expense)


def _author_action(request, pk, action):
    expense = Expense.objects.filter(pk=pk).first()
    if expense is None:
        raise Http404
    card = fetch_card(expense.card_id)
    if not card or card["author_id"] != request.user.id:
        raise Http404
    try:
        expense = action(expense, actor=request.user)
    except ExpenseActionError as exc:
        return Response({"detail": str(exc)}, status=400)
    return Response(ExpenseSerializer(expense).data)


class ModerationExpenseListView(generics.ListAPIView):
    permission_classes = [IsModerator]
    serializer_class = ModerationExpenseListSerializer
    pagination_class = None

    def get_queryset(self):
        return ExpenseRepository().pending()


class ExpenseModerationActionView(APIView):
    permission_classes = [IsModerator]
    comment_required = False

    def post(self, request, pk):
        expense = Expense.objects.filter(pk=pk).first()
        if expense is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = ExpenseModerationSerializer(
            data=request.data, context={"comment_required": self.comment_required}
        )
        serializer.is_valid(raise_exception=True)
        try:
            expense = self.perform_action(expense, serializer.validated_data, request.user)
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            ExpenseSerializer(
                expense,
                context={"request": request, "include_internal": True},
            ).data
        )

    def perform_action(self, expense, data, actor):
        raise NotImplementedError


class ExpenseApproveView(ExpenseModerationActionView):
    def perform_action(self, expense, data, actor):
        return approve_expense(
            expense,
            data.get("comment") or "",
            actor=actor,
            publish_receipt=data.get("publish_receipt"),
        )


class ExpenseRejectView(ExpenseModerationActionView):
    comment_required = True

    def perform_action(self, expense, data, actor):
        return reject_expense(expense, data["comment"], actor=actor)


class ExpenseRequestRevisionView(ExpenseModerationActionView):
    comment_required = True

    def perform_action(self, expense, data, actor):
        return request_expense_revision(
            expense,
            data["comment"],
            actor=actor,
            internal_comment=data.get("internal_comment") or "",
        )


class AdminExpenseListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminExpenseSerializer
    pagination_class = None
    queryset = Expense.objects.order_by("-created_at")


class InternalTotalsView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        totals = card_escrow_totals(pk)
        totals.update(public_report(pk))
        return Response(totals)


class InternalReconcileView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        report = reconcile_card(pk)
        return Response({"matched": report.matched, "differences": report.differences, "card_id": pk})


class InternalMarkPaidView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        expense = Expense.objects.filter(pk=pk).first()
        if expense is None:
            return Response({"detail": "Not found."}, status=404)
        try:
            expense = mark_expense_paid(expense, payout_id=request.data.get("payout_id"))
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ExpenseSerializer(expense).data)


class ExpenseOriginalView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        expense = Expense.objects.filter(pk=pk).first()
        if expense is None or not expense.original_file:
            raise Http404
        card = fetch_card(expense.card_id)
        if not can_see_private(request.user, card or {}):
            raise Http404
        log_sensitive_access(
            resource_type="expense",
            resource_id=expense.id,
            field_name="original_file",
            purpose="expense_review",
            request=request,
        )
        return FileResponse(expense.original_file.open("rb"), filename=expense.file_name or "receipt")

from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.audit import log_sensitive_access
from ekomek_common.auth import IsAuthor, IsModeratorOrAdmin
from ekomek_common.constants import Role

from .invoice_repositories import InvoiceRepository
from .invoice_serializers import (
    InvoiceCreateSerializer,
    InvoiceDecisionSerializer,
    InvoiceSerializer,
    PayoutCreateSerializer,
    PayoutSerializer,
)
from .invoice_services import cancel_invoice, reject_invoice, verify_invoice
from .payout_models import Invoice, Payout
from .payout_providers import get_payout_adapter
from .payout_providers.exceptions import InvalidPayoutSignature, PayoutConfigError, PayoutMismatchError, PayoutProviderError
from .payout_services import apply_payout_result, request_payout
from .reporting import card_is_public
from .workflow import ExpenseActionError, fetch_card


def can_see_private(user, card):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.role in Role.STAFF:
        return True
    return user.role == Role.AUTHOR and card["author_id"] == user.id


def _error(exc):
    code = getattr(exc, "status_code", 400)
    payload = {"detail": getattr(exc, "message", str(exc))}
    if getattr(exc, "code", None):
        payload["code"] = exc.code
    return Response(payload, status=code)


class CardInvoiceListCreateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        card = fetch_card(pk)
        if card is None:
            raise Http404
        if not (card_is_public(card) or can_see_private(request.user, card)):
            raise Http404
        if not can_see_private(request.user, card):
            raise Http404
        invoices = InvoiceRepository().for_card(pk)
        return Response(InvoiceSerializer(invoices, many=True, context={"request": request}).data)

    def post(self, request, pk):
        card = fetch_card(pk)
        if card is None or not request.user.is_authenticated or card["author_id"] != request.user.id:
            raise Http404
        serializer = InvoiceCreateSerializer(data=request.data, context={"request": request, "card": card})
        serializer.is_valid(raise_exception=True)
        try:
            invoice = serializer.save()
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(InvoiceSerializer(invoice).data, status=201)


class InvoiceCreateView(APIView):
    permission_classes = [IsAuthor]

    def post(self, request):
        card_id = request.data.get("card_id")
        card = fetch_card(card_id)
        if card is None or card["author_id"] != request.user.id:
            raise Http404
        serializer = InvoiceCreateSerializer(data=request.data, context={"request": request, "card": card})
        serializer.is_valid(raise_exception=True)
        try:
            invoice = serializer.save()
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(InvoiceSerializer(invoice).data, status=201)


class InvoiceDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        invoice = Invoice.objects.select_related("organization").filter(pk=pk).first()
        if invoice is None:
            raise Http404
        card = fetch_card(invoice.card_id)
        if not can_see_private(request.user, card or {}):
            raise Http404
        data = InvoiceSerializer(invoice).data
        data["payouts"] = PayoutSerializer(invoice.payouts.all(), many=True).data
        return Response(data)

    def patch(self, request, pk):
        return Response({"detail": "Статус счёта нельзя менять с клиента."}, status=405)

    def post(self, request, pk):
        return self.patch(request, pk)


class InvoiceOriginalView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        invoice = Invoice.objects.filter(pk=pk).first()
        if invoice is None or not invoice.original_file:
            raise Http404
        card = fetch_card(invoice.card_id)
        if not can_see_private(request.user, card or {}):
            raise Http404
        log_sensitive_access(
            resource_type="invoice",
            resource_id=invoice.id,
            field_name="original_file",
            purpose="invoice_review",
            request=request,
        )
        return FileResponse(invoice.original_file.open("rb"), filename=invoice.file_name or "invoice")


class InvoiceVerifyView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        invoice = Invoice.objects.filter(pk=pk).first()
        if invoice is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = InvoiceDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invoice = verify_invoice(invoice, serializer.validated_data.get("comment") or "", actor=request.user)
        except (ExpenseActionError, PayoutConfigError, PayoutProviderError) as exc:
            return _error(exc)
        return Response(InvoiceSerializer(invoice).data)


class InvoiceRejectView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, pk):
        invoice = Invoice.objects.filter(pk=pk).first()
        if invoice is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = InvoiceDecisionSerializer(data=request.data, context={"comment_required": True})
        serializer.is_valid(raise_exception=True)
        try:
            invoice = reject_invoice(invoice, serializer.validated_data["comment"], actor=request.user)
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(InvoiceSerializer(invoice).data)


class InvoiceCancelView(APIView):
    permission_classes = [IsAuthor]

    def post(self, request, pk):
        invoice = Invoice.objects.filter(pk=pk).first()
        if invoice is None:
            raise Http404
        card = fetch_card(invoice.card_id)
        if not card or card["author_id"] != request.user.id:
            raise Http404
        try:
            invoice = cancel_invoice(invoice, actor=request.user)
        except ExpenseActionError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(InvoiceSerializer(invoice).data)


class ModerationInvoiceListView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):
        invoices = InvoiceRepository().pending_review()
        return Response(InvoiceSerializer(invoices, many=True).data)


class PayoutCreateView(APIView):
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request):
        serializer = PayoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = Invoice.objects.filter(pk=serializer.validated_data["invoice_id"]).first()
        if invoice is None:
            return Response({"detail": "Not found."}, status=404)
        try:
            payout = request_payout(
                invoice,
                amount=serializer.validated_data.get("amount"),
                actor=request.user,
                idempotency_key=serializer.validated_data.get("idempotency_key"),
            )
        except (ExpenseActionError, PayoutConfigError, PayoutProviderError) as exc:
            return _error(exc)
        return Response(PayoutSerializer(payout).data, status=201)


class PayoutDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        payout = Payout.objects.select_related("organization", "invoice").filter(pk=pk).first()
        if payout is None:
            raise Http404
        card = fetch_card(payout.card_id)
        if not can_see_private(request.user, card or {}):
            raise Http404
        return Response(PayoutSerializer(payout).data)

    def patch(self, request, pk):
        return Response({"detail": "Статус выплаты нельзя менять с клиента."}, status=405)

    def post(self, request, pk):
        return self.patch(request, pk)


class PayoutWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, provider):
        try:
            adapter = get_payout_adapter(provider)
            payload = request.data
            if hasattr(payload, "dict"):
                payload = payload.dict()
            result = adapter.parse_result(payload, headers=request.headers, raw_body=request.body)
            payout = apply_payout_result(result)
        except (
            InvalidPayoutSignature,
            PayoutConfigError,
            PayoutProviderError,
            PayoutMismatchError,
            ExpenseActionError,
        ) as exc:
            return _error(exc)
        return Response(PayoutSerializer(payout).data)

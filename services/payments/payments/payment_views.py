from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Donation
from .payment_flow import (
    PaymentFlowError,
    apply_browser_outcome,
    apply_provider_result,
    complete_dev_payment,
)
from .providers import get_payment_adapter
from .providers.exceptions import (
    InvalidProviderSignature,
    PaymentConfigError,
    PaymentProviderError,
    ProviderMismatchError,
)
from .serializers import DonateSerializer, PaymentSessionSerializer
from .services import fetch_card


def _error_response(exc):
    code = getattr(exc, "status_code", 400)
    payload = {"detail": getattr(exc, "message", str(exc))}
    if getattr(exc, "code", None):
        payload["code"] = exc.code
    return Response(payload, status=code)


class PaymentSessionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        card_id = request.data.get("card_id")
        card = fetch_card(card_id)
        if card is None:
            return Response({"detail": "Not found."}, status=404)
        if card.get("status") != "active":
            return Response(
                {"detail": "Пожертвования принимаются только для активных сборов."},
                status=400,
            )
        serializer = DonateSerializer(data=request.data, context={"request": request, "card": card})
        serializer.is_valid(raise_exception=True)
        try:
            donation = serializer.save()
        except PaymentConfigError as exc:
            return _error_response(exc)
        except PaymentProviderError as exc:
            return _error_response(exc)
        return Response(PaymentSessionSerializer(donation).data, status=status.HTTP_201_CREATED)


class PaymentDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        donation = Donation.objects.filter(pk=pk).first()
        if donation is None:
            return Response({"detail": "Not found."}, status=404)
        return Response(PaymentSessionSerializer(donation).data)

    def patch(self, request, pk):
        return Response(
            {"detail": "Статус платежа нельзя менять с клиента."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        payment_id = request.query_params.get("payment")
        donation = Donation.objects.filter(pk=payment_id).first()
        if donation is None:
            return Response({"detail": "Not found."}, status=404)
        apply_browser_outcome(donation, request.query_params.get("outcome"))
        donation.refresh_from_db()
        return Response(PaymentSessionSerializer(donation).data)


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request, provider):
        try:
            adapter = get_payment_adapter(provider)
            payload = request.data
            if hasattr(payload, "dict"):
                payload = payload.dict()
            result = adapter.parse_result(
                payload,
                headers=request.headers,
                raw_body=request.body,
                script_name=provider,
            )
            donation = apply_provider_result(result)
            body, content_type = adapter.success_response(script_name=provider)
        except (
            InvalidProviderSignature,
            PaymentConfigError,
            PaymentProviderError,
            ProviderMismatchError,
            PaymentFlowError,
        ) as exc:
            return _error_response(exc)
        if content_type == "application/xml":
            return HttpResponse(body, content_type=content_type)
        return Response(PaymentSessionSerializer(donation).data)


class DevPaymentCompleteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        try:
            adapter = get_payment_adapter()
        except PaymentConfigError as exc:
            return _error_response(exc)
        if adapter.name != "dev":
            return Response({"detail": "Not found."}, status=404)
        donation = Donation.objects.filter(pk=pk).first()
        if donation is None:
            return Response({"detail": "Not found."}, status=404)
        outcome = request.data.get("outcome") or "failed"
        if outcome not in {"success", "failed", "canceled"}:
            return Response({"detail": "Некорректный результат."}, status=400)
        try:
            donation = complete_dev_payment(donation, outcome)
        except (PaymentProviderError, PaymentFlowError, ProviderMismatchError) as exc:
            return _error_response(exc)
        return Response(PaymentSessionSerializer(donation).data)

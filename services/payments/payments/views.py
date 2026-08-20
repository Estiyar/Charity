from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ekomek_common.auth import IsAdmin
from ekomek_common.http import ServiceClientError, cards_client, documents_client

from .models import Donation, PaymentStatus, RefundDecision, RefundDecisionStatus
from .providers.exceptions import PaymentConfigError, PaymentProviderError
from .serializers import (
    AdminDonationSerializer,
    DonateSerializer,
    DonationSerializer,
    MyDonationSerializer,
    PaymentSessionSerializer,
    RefundDecisionChooseSerializer,
    RefundDecisionSerializer,
)
from .redistribution import (
    RefundDecisionError,
    apply_redistribution_choice,
)
from .services import DONOR_REFUND_DISABLED_MESSAGE, fetch_card


class DonateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        card = fetch_card(pk)
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
        except (PaymentConfigError, PaymentProviderError) as exc:
            return Response({"detail": exc.message, "code": exc.code}, status=exc.status_code)
        return Response(
            {
                "donation": PaymentSessionSerializer(donation).data,
                "redirect_url": donation.redirect_url,
                "payment_status": donation.payment_status,
                "message": "Перенаправление на страницу оплаты.",
            },
            status=201,
        )


class DonationListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DonationSerializer
    pagination_class = None

    def get_queryset(self):
        card = fetch_card(self.kwargs["pk"])
        if card is None or card.get("status") not in {"active", "completed", "redistribution"}:
            from django.http import Http404
            raise Http404
        return Donation.objects.filter(
            card_id=card["id"],
            payment_status=PaymentStatus.SUCCESS,
        ).order_by("-created_at")


class MyDonationsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyDonationSerializer
    pagination_class = None

    def get_queryset(self):
        return Donation.objects.filter(donor_id=self.request.user.id).order_by("-created_at")


class MyRefundDecisionsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RefundDecisionSerializer
    pagination_class = None

    def get_queryset(self):
        return RefundDecision.objects.filter(
            donor_id=self.request.user.id,
            status=RefundDecisionStatus.PENDING,
        ).select_related("donation").order_by("deadline")


class MyRefundHistoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RefundDecisionSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            RefundDecision.objects.filter(donor_id=self.request.user.id)
            .exclude(status=RefundDecisionStatus.PENDING)
            .select_related("donation")
            .order_by("-resolved_at", "-id")
        )


class RefundDecisionChooseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        decision = RefundDecision.objects.filter(pk=pk, donor_id=request.user.id).first()
        if decision is None:
            return Response({"detail": "Not found."}, status=404)
        serializer = RefundDecisionChooseSerializer(data=request.data, context={"decision": decision})
        serializer.is_valid(raise_exception=True)
        try:
            decision = apply_redistribution_choice(
                decision,
                serializer.validated_data["choice"],
                target_card=serializer.validated_data.get("target_card"),
            )
        except RefundDecisionError as exc:
            if exc.field:
                return Response({exc.field: [exc.message]}, status=400)
            return Response({"detail": exc.message}, status=400)
        return Response(RefundDecisionSerializer(decision).data)


class ClosedRefundApiView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk=None):
        return self._gone()

    def post(self, request, pk=None):
        return self._gone()

    def _gone(self):
        return Response(
            {
                "detail": DONOR_REFUND_DISABLED_MESSAGE,
                "code": "refund_disabled",
            },
            status=410,
        )


class MyRedistributionListView(MyRefundDecisionsListView):
    pass


class MyRedistributionHistoryListView(MyRefundHistoryListView):
    pass


class RedistributionChooseView(RefundDecisionChooseView):
    pass


class PlatformStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        active_fundraisers = 0
        total_collected = DecimalSafe("0")
        try:
            cards = cards_client().get("/internal/cards/", params={"status": "active"})
            active_fundraisers = len(cards)
            all_public = []
            for status_name in ("active", "completed", "redistribution"):
                all_public.extend(cards_client().get("/internal/cards/", params={"status": status_name}))
            total_collected = sum(DecimalSafe(card.get("collected_amount")) for card in all_public)
        except ServiceClientError:
            pass
        verified_documents = 0
        try:
            verified_documents = documents_client().get("/internal/stats/").get("verified_documents", 0)
        except ServiceClientError:
            pass
        donors_count = Donation.objects.filter(payment_status=PaymentStatus.SUCCESS).values("donor_name").distinct().count()
        return Response(
            {
                "active_fundraisers": active_fundraisers,
                "total_collected": str(total_collected),
                "donors_count": donors_count,
                "verified_documents": verified_documents,
            }
        )


def DecimalSafe(value):
    from decimal import Decimal

    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


class AdminDonationListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminDonationSerializer
    pagination_class = None
    queryset = Donation.objects.order_by("-created_at")

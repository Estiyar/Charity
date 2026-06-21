from django.db.models import F, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus, PUBLIC_STATUSES
from apps.documents.models import Document, DocumentStatus

from .models import Donation, RefundDecision, RefundDecisionStatus
from .serializers import (
    DONATION_SUCCESS_MESSAGE,
    DonateSerializer,
    DonationSerializer,
    MyDonationSerializer,
    RefundDecisionChooseSerializer,
    RefundDecisionSerializer,
)
from .services import RefundDecisionError, apply_refund_choice


class PublicCardMixin:
    def get_public_card(self, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        if card.status not in PUBLIC_STATUSES:
            raise Http404
        return card


class DonateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        if card.status != CardStatus.ACTIVE:
            return Response(
                {"detail": "Пожертвования принимаются только для активных сборов."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = DonateSerializer(
            data=request.data,
            context={"request": request, "card": card},
        )
        serializer.is_valid(raise_exception=True)
        donation = serializer.save()
        FundraisingCard.objects.filter(pk=card.pk).update(
            collected_amount=F("collected_amount") + donation.amount
        )
        card.refresh_from_db()
        return Response(
            {
                "donation": DonationSerializer(donation).data,
                "message": DONATION_SUCCESS_MESSAGE,
                "collected_amount": str(card.collected_amount),
            },
            status=status.HTTP_201_CREATED,
        )


class DonationListView(PublicCardMixin, generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DonationSerializer
    pagination_class = None

    def get_queryset(self):
        card = self.get_public_card(self.kwargs["pk"])
        return Donation.objects.filter(card=card).order_by("-created_at")


class MyDonationsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyDonationSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Donation.objects.filter(donor=self.request.user)
            .select_related("card")
            .order_by("-created_at")
        )


class MyRefundDecisionsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RefundDecisionSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            RefundDecision.objects.filter(
                donor=self.request.user,
                status=RefundDecisionStatus.PENDING,
            )
            .select_related("card", "donation", "target_card")
            .order_by("deadline")
        )


class MyRefundHistoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RefundDecisionSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            RefundDecision.objects.filter(donor=self.request.user)
            .exclude(status=RefundDecisionStatus.PENDING)
            .select_related("card", "donation", "target_card")
            .order_by("-resolved_at", "-id")
        )


class RefundDecisionChooseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        decision = get_object_or_404(
            RefundDecision.objects.select_related("card"),
            pk=pk,
            donor=request.user,
        )
        serializer = RefundDecisionChooseSerializer(
            data=request.data,
            context={"decision": decision},
        )
        serializer.is_valid(raise_exception=True)
        try:
            decision = apply_refund_choice(
                decision,
                serializer.validated_data["choice"],
                target_card=serializer.validated_data.get("target_card"),
            )
        except RefundDecisionError as exc:
            if exc.field:
                return Response(
                    {exc.field: [exc.message]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RefundDecisionSerializer(decision).data)


class PlatformStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        active_cards = FundraisingCard.objects.filter(status="active").count()
        total_collected = (
            FundraisingCard.objects.filter(status__in=PUBLIC_STATUSES).aggregate(
                total=Sum("collected_amount")
            )["total"]
            or 0
        )
        donors_count = Donation.objects.values("donor_name").distinct().count()
        verified_documents = Document.objects.filter(
            status=DocumentStatus.VERIFIED
        ).count()
        return Response(
            {
                "active_fundraisers": active_cards,
                "total_collected": str(total_collected),
                "donors_count": donors_count,
                "verified_documents": verified_documents,
            }
        )

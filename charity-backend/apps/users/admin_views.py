from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cards.models import City, Diagnosis, FundraisingCard
from apps.common.card_status import transition, InvalidStatusTransition
from apps.donations.models import Donation
from apps.expenses.models import Expense
from apps.moderation.models import ModerationLog
from apps.moderation.services import log_moderation_action
from apps.users.models import PlatformSettings, Role, User
from apps.users.permissions import IsAdmin

from .admin_serializers import (
    AdminCardSerializer,
    AdminCardStatusSerializer,
    AdminDonationSerializer,
    AdminExpenseSerializer,
    AdminModerationLogSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    CitySerializer,
    DiagnosisSerializer,
    PlatformSettingsSerializer,
)


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer
    pagination_class = None
    queryset = User.objects.order_by("-created_at")


class AdminUserDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "role" in data:
            user.role = data["role"]
        if "status" in data:
            user.status = data["status"]
        user.save()
        return Response(AdminUserSerializer(user).data)


class AdminModeratorListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer
    pagination_class = None

    def get_queryset(self):
        return User.objects.filter(role=Role.MODERATOR).order_by("full_name")


class AdminCardListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminCardSerializer
    pagination_class = None
    queryset = FundraisingCard.objects.select_related("author").order_by("-created_at")


class AdminCardStatusView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        serializer = AdminCardStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            transition(card, serializer.validated_data["status"])
        except InvalidStatusTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        from apps.donations.services import handle_card_status_change

        handle_card_status_change(card, card.status)
        return Response(AdminCardSerializer(card).data)


class AdminCardSetStatusView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        card = get_object_or_404(FundraisingCard, pk=pk)
        serializer = AdminCardStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        old_status = card.status
        if old_status != new_status:
            card.status = new_status
            card.save(update_fields=["status", "updated_at"])
            log_moderation_action(
                card,
                request.user,
                "admin_set_status",
                f"{old_status} -> {new_status}",
            )
            from apps.donations.services import handle_card_status_change

            handle_card_status_change(card, new_status)
        return Response(AdminCardSerializer(card).data)


class AdminDonationListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminDonationSerializer
    pagination_class = None

    def get_queryset(self):
        return Donation.objects.select_related("card").order_by("-created_at")


class AdminExpenseListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminExpenseSerializer
    pagination_class = None

    def get_queryset(self):
        return Expense.objects.select_related("card").order_by("-created_at")


class AdminModerationLogListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminModerationLogSerializer
    pagination_class = None

    def get_queryset(self):
        return ModerationLog.objects.select_related("card", "moderator").order_by(
            "-created_at"
        )


class AdminCityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = CitySerializer
    pagination_class = None
    queryset = City.objects.order_by("name")


class AdminCityDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = City.objects.all()


class AdminDiagnosisListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = DiagnosisSerializer
    pagination_class = None
    queryset = Diagnosis.objects.order_by("name")


class AdminDiagnosisDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = Diagnosis.objects.all()


class AdminSettingsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        settings = PlatformSettings.get_solo()
        return Response(PlatformSettingsSerializer(settings).data)

    def patch(self, request):
        settings = PlatformSettings.get_solo()
        serializer = PlatformSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

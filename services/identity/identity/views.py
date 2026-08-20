from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from ekomek_common.audit import reveal_encrypted
from ekomek_common.auth import HasInternalToken, IsAdmin
from ekomek_common.constants import Role
from ekomek_common.outbox import enqueue_event

from .ecp import issue_challenge, consume_challenge
from .ecp_services import EcpFlowError, verify_ecp_signature
from .models import User
from .repositories import BalanceTransactionRepository, UserRepository
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    BalanceTransactionSerializer,
    BalanceWithdrawSerializer,
    EcpRegisterSerializer,
    EcpVerifySerializer,
    InternalUserSerializer,
    InternalUserUpdateSerializer,
    LoginSerializer,
    MeSerializer,
    RegisterSerializer,
)
from .services import (
    BalanceError,
    apply_identity_corrections,
    credit_user_balance,
    withdraw_user_balance,
)


def format_balance_amount(value):
    return str(Decimal(value).quantize(Decimal("0.01")))


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(MeSerializer(user).data, status=status.HTTP_201_CREATED)


class EcpChallengeView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        challenge_id, challenge, ttl = issue_challenge()
        return Response(
            {
                "challenge_id": challenge_id,
                "challenge": challenge,
                "expires_in": ttl,
            }
        )


class EcpVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = EcpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = verify_ecp_signature(
                serializer.validated_data["challenge_id"],
                serializer.validated_data["cms"],
            )
        except EcpFlowError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code},
                status=exc.status_code,
            )
        return Response(payload)


class EcpRegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = EcpRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(MeSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = LoginSerializer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = UserRepository().get_by_id(request.user.id)
        return Response(MeSerializer(user).data)


class BalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = UserRepository().get_by_id(request.user.id)
        transactions = BalanceTransactionRepository().list_for_user(user)
        return Response(
            {
                "balance": format_balance_amount(user.balance),
                "transactions": BalanceTransactionSerializer(transactions, many=True).data,
            }
        )


class BalanceWithdrawView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BalanceWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(pk=request.user.pk)
        amount = serializer.validated_data.get("amount")
        if amount is None:
            amount = user.balance
        try:
            user, transaction_record = withdraw_user_balance(user, amount)
        except BalanceError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "message": "Заявка на вывод принята",
                "balance": format_balance_amount(user.balance),
                "transaction": BalanceTransactionSerializer(transaction_record).data,
            }
        )


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = UserRepository().list_all()
        return Response(AdminUserSerializer(users, many=True).data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if user is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "role" in data:
            user.role = data["role"]
            if data["role"] == Role.ADMIN:
                user.is_staff = True
                user.is_superuser = True
            enqueue_event("user.role_changed", "user", user.id, {"user_id": user.id, "role": user.role})
        if "status" in data:
            user.status = data["status"]
            if data["status"] == "blocked":
                enqueue_event("user.blocked", "user", user.id, {"user_id": user.id})
        identity_fields = {
            field: data[field] for field in ("full_name", "birth_date") if field in data
        }
        if identity_fields:
            apply_identity_corrections(user, identity_fields, actor="admin")
        else:
            user.save()
        return Response(AdminUserSerializer(user).data)


class AdminModeratorListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = UserRepository().list_moderators()
        return Response(AdminUserSerializer(users, many=True).data)


class InternalCreditView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if user is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        amount = Decimal(str(request.data.get("amount", "0")))
        description = request.data.get("description", "")
        purpose = request.data.get("purpose", "")
        try:
            user = credit_user_balance(user, amount, description, purpose=purpose)
        except BalanceError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_410_GONE)
        return Response({"balance": format_balance_amount(user.balance)})


class InternalUserView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def get(self, request, pk):
        user = UserRepository().get_by_id(pk)
        if user is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = InternalUserSerializer(user).data
        if request.query_params.get("reveal") == "1":
            payload["iin"] = reveal_encrypted(
                user.iin_encrypted,
                resource_type="user",
                resource_id=user.id,
                field_name="iin",
                purpose="recipient_verification",
                request=request,
                actor_role="internal",
            )
        return Response(payload)

    def patch(self, request, pk):
        user = UserRepository().get_by_id(pk)
        if user is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = InternalUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data:
            return Response(InternalUserSerializer(user).data)
        user = apply_identity_corrections(user, dict(serializer.validated_data), actor="internal")
        return Response(InternalUserSerializer(user).data)


class InternalConsumeChallengeView(APIView):
    authentication_classes = []
    permission_classes = [HasInternalToken]

    def post(self, request):
        challenge = consume_challenge(request.data.get("challenge_id"))
        if challenge is None:
            return Response({"detail": "Challenge истёк или уже использован."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"challenge": challenge})

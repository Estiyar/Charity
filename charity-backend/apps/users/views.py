from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import BalanceTransaction, User
from .services import BalanceError, withdraw_user_balance
from .serializers import (
    BalanceTransactionSerializer,
    BalanceWithdrawSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
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
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


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
        return Response(UserSerializer(request.user).data)


class BalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        transactions = BalanceTransaction.objects.filter(user=user).order_by("-created_at")
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


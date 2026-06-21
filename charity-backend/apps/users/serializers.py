from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.antifraud.services import is_high_risk
from apps.common.validators import validate_iin

from .models import BalanceTransaction, Role, User


class BalanceTransactionSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_transaction_type_display", read_only=True)

    class Meta:
        model = BalanceTransaction
        fields = (
            "id",
            "amount",
            "transaction_type",
            "type_label",
            "description",
            "created_at",
        )
        read_only_fields = fields


class BalanceWithdrawSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.01"),
    )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "email",
            "phone",
            "iin",
            "role",
            "status",
            "created_at",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    repeat_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "full_name",
            "email",
            "phone",
            "iin",
            "password",
            "repeat_password",
            "role",
        )

    def validate_iin(self, value):
        validate_iin(value)
        return value

    def validate_role(self, value):
        if value not in (Role.DONOR, Role.AUTHOR):
            raise serializers.ValidationError(
                "При регистрации можно выбрать только роль donor или author."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["repeat_password"]:
            raise serializers.ValidationError(
                {"repeat_password": "Пароли не совпадают."}
            )
        validate_password(attrs["password"])
        if attrs["role"] == Role.AUTHOR and is_high_risk(attrs["iin"]):
            raise serializers.ValidationError(
                {"iin": "Регистрация невозможна: высокий уровень риска."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("repeat_password")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.is_blocked:
            raise serializers.ValidationError("Пользователь заблокирован.")
        return data

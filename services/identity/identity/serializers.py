from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from ekomek_common.constants import Role, UserStatus
from ekomek_common.validators import validate_iin

from .models import BalanceTransaction, User
from .repositories import UserRepository
from .services import register_user


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
    phone = serializers.CharField(source="phone_masked", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "email",
            "phone",
            "iin_masked",
            "birth_date",
            "role",
            "status",
            "ecp_locked_fields",
            "certificate_type",
            "created_at",
        )
        read_only_fields = fields


class MeSerializer(UserSerializer):
    phone = serializers.SerializerMethodField()

    def get_phone(self, obj):
        return obj.decrypted_phone() or obj.phone_masked


class AdminUserSerializer(UserSerializer):
    pass


class InternalUserSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="phone_masked", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "email",
            "phone",
            "iin_hash",
            "iin_masked",
            "birth_date",
            "role",
            "status",
            "ecp_verification_id",
            "ecp_locked_fields",
            "last_login",
            "created_at",
        )
        read_only_fields = fields


class InternalUserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False)
    birth_date = serializers.DateField(required=False, allow_null=True)


class InternalUserSetStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=UserStatus.ALL)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AdminUserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.ALL, required=False)
    status = serializers.ChoiceField(choices=UserStatus.ALL, required=False)
    full_name = serializers.CharField(max_length=255, required=False)
    birth_date = serializers.DateField(required=False, allow_null=True)


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True)
    iin = serializers.CharField()
    password = serializers.CharField(write_only=True)
    repeat_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[(Role.DONOR, Role.DONOR), (Role.AUTHOR, Role.AUTHOR)])
    personal_data_consent = serializers.BooleanField()

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return email

    def validate_iin(self, value):
        validate_iin(value)
        if UserRepository().iin_exists(value):
            raise serializers.ValidationError("Пользователь с таким ИИН уже зарегистрирован.")
        return value

    def validate_role(self, value):
        if value not in (Role.DONOR, Role.AUTHOR):
            raise serializers.ValidationError(
                "При регистрации можно выбрать только роль donor или author."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["repeat_password"]:
            raise serializers.ValidationError({"repeat_password": "Пароли не совпадают."})
        validate_password(attrs["password"])
        if not attrs.get("personal_data_consent"):
            raise serializers.ValidationError(
                {"personal_data_consent": "Необходимо согласие на обработку персональных данных."}
            )
        return attrs

    def create(self, validated_data):
        from .ecp_services import resolve_legacy_status

        validated_data.pop("repeat_password")
        validated_data.pop("personal_data_consent")
        password = validated_data.pop("password")
        validated_data["status"] = resolve_legacy_status(validated_data["role"], validated_data["iin"])
        user = User.objects.create_user(password=password, **validated_data)
        return register_user(user)


class LoginSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        token["iin_hash"] = user.iin_hash or ""
        token["full_name"] = user.full_name
        token["status"] = user.status
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.is_blocked or not self.user.can_login:
            raise serializers.ValidationError("Пользователь заблокирован.")
        return data


class EcpVerifySerializer(serializers.Serializer):
    challenge_id = serializers.CharField()
    cms = serializers.CharField()


class EcpRegisterSerializer(serializers.Serializer):
    ecp_session_token = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    repeat_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[(Role.DONOR, Role.DONOR), (Role.AUTHOR, Role.AUTHOR)])
    personal_data_consent = serializers.BooleanField()

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return email

    def validate_phone(self, value):
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) < 10:
            raise serializers.ValidationError("Укажите корректный номер телефона.")
        return value

    def validate_role(self, value):
        if value not in (Role.DONOR, Role.AUTHOR):
            raise serializers.ValidationError(
                "При регистрации можно выбрать только роль donor или author."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["repeat_password"]:
            raise serializers.ValidationError({"repeat_password": "Пароли не совпадают."})
        validate_password(attrs["password"])
        if not attrs.get("personal_data_consent"):
            raise serializers.ValidationError(
                {"personal_data_consent": "Необходимо согласие на обработку персональных данных."}
            )
        return attrs

    def create(self, validated_data):
        from .ecp_services import EcpFlowError, register_with_ecp

        validated_data.pop("repeat_password")
        validated_data.pop("personal_data_consent")
        try:
            return register_with_ecp(validated_data)
        except EcpFlowError as exc:
            raise serializers.ValidationError({"non_field_errors": [exc.message]}) from exc


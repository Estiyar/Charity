from rest_framework import serializers

from apps.cards.models import City, Diagnosis, FundraisingCard
from apps.common.card_status import CardStatus
from apps.donations.models import Donation
from apps.expenses.models import Expense
from apps.moderation.models import ModerationLog
from apps.users.models import PlatformSettings, Role, User, UserStatus


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "email",
            "phone",
            "role",
            "status",
            "created_at",
        )
        read_only_fields = fields


class AdminUserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.choices, required=False)
    status = serializers.ChoiceField(choices=UserStatus.choices, required=False)


class AdminCardSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = FundraisingCard
        fields = (
            "id",
            "full_name",
            "author_name",
            "diagnosis",
            "city",
            "status",
            "target_amount",
            "collected_amount",
            "end_date",
            "created_at",
        )
        read_only_fields = fields


class AdminCardStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=CardStatus.choices)


class AdminDonationSerializer(serializers.ModelSerializer):
    card_name = serializers.CharField(source="card.full_name", read_only=True)

    class Meta:
        model = Donation
        fields = (
            "id",
            "card_id",
            "card_name",
            "donor_name",
            "amount",
            "payment_method",
            "created_at",
        )
        read_only_fields = fields


class AdminExpenseSerializer(serializers.ModelSerializer):
    card_name = serializers.CharField(source="card.full_name", read_only=True)

    class Meta:
        model = Expense
        fields = (
            "id",
            "card_id",
            "card_name",
            "date",
            "purpose",
            "amount",
            "status",
            "created_at",
        )
        read_only_fields = fields


class AdminModerationLogSerializer(serializers.ModelSerializer):
    card_name = serializers.CharField(source="card.full_name", read_only=True)
    moderator_name = serializers.CharField(source="moderator.full_name", read_only=True)

    class Meta:
        model = ModerationLog
        fields = (
            "id",
            "card_id",
            "card_name",
            "action",
            "comment",
            "moderator_name",
            "created_at",
        )
        read_only_fields = fields


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name")


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ("id", "name")


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = (
            "site_name",
            "demo_payment_enabled",
            "bank_integration_stub",
            "escrow_integration_stub",
            "pdf_auto_check_stub",
            "notifications_stub",
            "egov_integration_stub",
            "refund_commission_percent",
            "refund_deadline_days",
            "updated_at",
        )

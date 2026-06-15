from decimal import Decimal

from rest_framework import serializers

from apps.common.card_status import CardStatus

from .models import Donation, PaymentStatus

DONATION_SUCCESS_MESSAGE = (
    "Спасибо за помощь! В MVP-версии это демо-платёж. "
    "В промышленной версии деньги будут перечисляться через платёжный шлюз на эскроу-счёт."
)

DONATABLE_STATUSES = {CardStatus.ACTIVE}


class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = (
            "id",
            "donor_name",
            "amount",
            "payment_method",
            "payment_status",
            "created_at",
        )
        read_only_fields = fields


class MyDonationSerializer(serializers.ModelSerializer):
    card_id = serializers.IntegerField(source="card.id", read_only=True)
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
            "payment_status",
            "created_at",
        )
        read_only_fields = fields


class DonateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("1"))
    donor_name = serializers.CharField(max_length=255)
    contact = serializers.CharField(max_length=255)
    payment_method = serializers.CharField(max_length=64)
    personal_data_consent = serializers.BooleanField()

    def validate_personal_data_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "Consent to personal data processing is required."
            )
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        card = self.context["card"]
        if card.status not in DONATABLE_STATUSES:
            raise serializers.ValidationError(
                "Donations are only accepted for active fundraising cards."
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("contact")
        validated_data.pop("personal_data_consent")
        request = self.context["request"]
        card = self.context["card"]
        donor = request.user if request.user.is_authenticated else None
        return Donation.objects.create(
            card=card,
            donor=donor,
            donor_name=validated_data["donor_name"],
            amount=validated_data["amount"],
            payment_method=validated_data["payment_method"],
            payment_status=PaymentStatus.SUCCESS,
        )

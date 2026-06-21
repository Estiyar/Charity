from decimal import Decimal

from rest_framework import serializers

from apps.cards.models import FundraisingCard
from apps.common.card_status import CardStatus
from apps.users.models import PlatformSettings

from .models import Donation, PaymentStatus, RefundChoice, RefundDecision
from .services import (
    RefundDecisionError,
    calculate_refund_payout,
    get_redirect_candidates,
    is_own_fundraiser,
    OWN_FUNDRAISER_DONATION_MESSAGE,
    validate_redirect_target,
)

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
        request = self.context["request"]
        if card.status not in DONATABLE_STATUSES:
            raise serializers.ValidationError(
                "Donations are only accepted for active fundraising cards."
            )
        if is_own_fundraiser(request.user, card):
            raise serializers.ValidationError(OWN_FUNDRAISER_DONATION_MESSAGE)
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


class RefundRedirectOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundraisingCard
        fields = ("id", "full_name", "diagnosis", "city", "collected_amount", "target_amount")
        read_only_fields = fields


class RefundDecisionCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundraisingCard
        fields = ("id", "full_name", "diagnosis", "city", "status")
        read_only_fields = fields


class RefundDecisionSerializer(serializers.ModelSerializer):
    card = RefundDecisionCardSerializer(read_only=True)
    target_card = RefundDecisionCardSerializer(read_only=True)
    donation_id = serializers.IntegerField(source="donation.id", read_only=True)
    redirect_options = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    refund_payout = serializers.SerializerMethodField()
    choice_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = RefundDecision
        fields = (
            "id",
            "donation_id",
            "card",
            "target_card",
            "share_amount",
            "choice",
            "choice_label",
            "status",
            "status_label",
            "deadline",
            "created_at",
            "resolved_at",
            "options",
            "redirect_options",
            "refund_payout",
        )
        read_only_fields = fields

    def get_choice_label(self, obj):
        if obj.choice == RefundChoice.EMPTY:
            return ""
        return obj.get_choice_display()

    def get_status_label(self, obj):
        return obj.get_status_display()

    def get_options(self, obj):
        return [
            {"value": RefundChoice.KEEP, "label": "Оставить семье получателя"},
            {"value": RefundChoice.REFUND, "label": "Вернуть на счёт"},
            {"value": RefundChoice.REDIRECT, "label": "Перенаправить на другой сбор"},
        ]

    def get_redirect_options(self, obj):
        candidates = get_redirect_candidates(obj.card)
        return RefundRedirectOptionSerializer(candidates, many=True).data

    def get_refund_payout(self, obj):
        settings = PlatformSettings.get_solo()
        payout, _commission = calculate_refund_payout(
            obj.share_amount,
            settings.refund_commission_percent,
        )
        return {
            "gross_amount": str(obj.share_amount),
            "commission_percent": settings.refund_commission_percent,
            "net_amount": str(payout),
        }


class RefundDecisionChooseSerializer(serializers.Serializer):
    choice = serializers.ChoiceField(choices=RefundChoice.choices)
    target_card_id = serializers.IntegerField(required=False)

    def validate_choice(self, value):
        if value == RefundChoice.EMPTY:
            raise serializers.ValidationError("Выберите один из вариантов распределения.")
        if value not in {RefundChoice.KEEP, RefundChoice.REFUND, RefundChoice.REDIRECT}:
            raise serializers.ValidationError("Недопустимый вариант распределения.")
        return value

    def validate(self, attrs):
        decision = self.context["decision"]
        choice = attrs["choice"]
        target_card = None
        if choice == RefundChoice.REDIRECT:
            target_card_id = attrs.get("target_card_id")
            if not target_card_id:
                raise serializers.ValidationError(
                    {"target_card_id": "Укажите целевой сбор для перенаправления."}
                )
            target_card = FundraisingCard.objects.filter(pk=target_card_id).first()
            if target_card is None:
                raise serializers.ValidationError(
                    {"target_card_id": "Целевой сбор не найден."}
                )
            try:
                validate_redirect_target(decision.card, target_card)
            except RefundDecisionError as exc:
                raise serializers.ValidationError({exc.field or "target_card_id": [exc.message]}) from exc
        attrs["target_card"] = target_card
        return attrs

from decimal import Decimal

from rest_framework import serializers

from ekomek_common.constants import CardStatus

from .models import Donation, RefundChoice, RefundDecision
from .payment_flow import PaymentFlowError, create_payment_session
from .services import (
    OWN_FUNDRAISER_DONATION_MESSAGE,
    PUBLIC_REDISTRIBUTION_CHOICES,
    PUBLIC_REDISTRIBUTION_OPTIONS,
    calculate_refund_payout,
    get_redirect_candidates,
    is_own_fundraiser,
    platform_settings,
    validate_redirect_target,
    RefundDecisionError,
    DONOR_REFUND_DISABLED_MESSAGE,
)

DONATABLE_STATUSES = {CardStatus.ACTIVE}


class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = ("id", "donor_name", "amount", "currency", "payment_method", "payment_status", "created_at")
        read_only_fields = fields


class MyDonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = (
            "id",
            "card_id",
            "card_name",
            "donor_name",
            "amount",
            "currency",
            "payment_method",
            "payment_status",
            "provider",
            "created_at",
            "paid_at",
        )
        read_only_fields = fields


class PaymentSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = (
            "id",
            "card_id",
            "amount",
            "currency",
            "donor_name",
            "email",
            "phone",
            "payment_method",
            "provider",
            "provider_payment_id",
            "payment_status",
            "idempotency_key",
            "redirect_url",
            "failed_reason",
            "created_at",
            "paid_at",
        )
        read_only_fields = fields


class DonateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("1"))
    donor_name = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    contact = serializers.CharField(max_length=255, required=False, allow_blank=True)
    payment_method = serializers.CharField(max_length=64)
    personal_data_consent = serializers.BooleanField()
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True)

    def validate_personal_data_consent(self, value):
        if not value:
            raise serializers.ValidationError("Consent to personal data processing is required.")
        return value

    def validate(self, attrs):
        card = self.context["card"]
        request = self.context["request"]
        if card.get("status") not in DONATABLE_STATUSES:
            raise serializers.ValidationError("Donations are only accepted for active fundraising cards.")
        if is_own_fundraiser(request.user, card):
            raise serializers.ValidationError(OWN_FUNDRAISER_DONATION_MESSAGE)
        contact = (attrs.get("contact") or "").strip()
        email = (attrs.get("email") or "").strip()
        phone = (attrs.get("phone") or "").strip()
        if contact and "@" in contact and not email:
            email = contact
        elif contact and not phone:
            phone = contact
        if not email and not phone:
            raise serializers.ValidationError({"contact": "Укажите email или телефон."})
        attrs["email"] = email
        attrs["phone"] = phone
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        card = self.context["card"]
        donor = request.user if request.user.is_authenticated else None
        validated_data.pop("personal_data_consent", None)
        validated_data.pop("contact", None)
        try:
            return create_payment_session(card, donor, validated_data)
        except PaymentFlowError as exc:
            if exc.field:
                raise serializers.ValidationError({exc.field: [exc.message]}) from exc
            raise serializers.ValidationError(exc.message) from exc


class RefundDecisionSerializer(serializers.ModelSerializer):
    card = serializers.JSONField(source="card_snapshot", read_only=True)
    target_card = serializers.JSONField(source="target_card_snapshot", read_only=True)
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
        return list(PUBLIC_REDISTRIBUTION_OPTIONS)

    def get_redirect_options(self, obj):
        return get_redirect_candidates(obj.card_snapshot or {"id": obj.card_id})

    def get_refund_payout(self, obj):
        if obj.choice != RefundChoice.REFUND:
            return None
        settings = platform_settings()
        payout, _commission = calculate_refund_payout(
            obj.share_amount, settings.get("refund_commission_percent", 10)
        )
        return {
            "gross_amount": str(obj.share_amount),
            "commission_percent": settings.get("refund_commission_percent", 10),
            "net_amount": str(payout),
        }


class RefundDecisionChooseSerializer(serializers.Serializer):
    choice = serializers.ChoiceField(choices=RefundChoice.choices)
    target_card_id = serializers.IntegerField(required=False)

    def validate_choice(self, value):
        if value == RefundChoice.REFUND:
            raise serializers.ValidationError(DONOR_REFUND_DISABLED_MESSAGE)
        if value not in PUBLIC_REDISTRIBUTION_CHOICES:
            raise serializers.ValidationError("Недопустимый вариант распределения.")
        return value

    def validate(self, attrs):
        from .services import fetch_card

        decision = self.context["decision"]
        target_card = None
        if attrs["choice"] == RefundChoice.REDIRECT:
            target_card_id = attrs.get("target_card_id")
            if not target_card_id:
                raise serializers.ValidationError(
                    {"target_card_id": "Укажите целевой сбор для перенаправления."}
                )
            target_card = fetch_card(target_card_id)
            if target_card is None:
                raise serializers.ValidationError({"target_card_id": "Целевой сбор не найден."})
            try:
                validate_redirect_target(decision.card_snapshot or {"id": decision.card_id}, target_card)
            except RefundDecisionError as exc:
                raise serializers.ValidationError({exc.field or "target_card_id": [exc.message]}) from exc
        attrs["target_card"] = target_card
        return attrs


class AdminDonationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donation
        fields = (
            "id",
            "card_id",
            "card_name",
            "donor_name",
            "amount",
            "currency",
            "payment_method",
            "provider",
            "provider_payment_id",
            "payment_status",
            "created_at",
            "paid_at",
            "failed_reason",
        )
        read_only_fields = fields

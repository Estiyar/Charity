from rest_framework import serializers

from ekomek_common.constants import EXPENSE_CARD_STATUSES
from ekomek_common.validators import validate_upload

from .invoice_services import create_invoice
from .payout_models import Invoice, OrganizationKind, Payout, VerifiedOrganization
from .workflow import escrow_available


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerifiedOrganization
        fields = (
            "id",
            "name",
            "kind",
            "bin_masked",
            "iban_masked",
            "bank_name",
            "verification_status",
            "verified_at",
        )
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    original_url = serializers.SerializerMethodField()
    public_receipt_url = serializers.SerializerMethodField()
    remaining_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    purpose = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = (
            "id",
            "card_id",
            "card_name",
            "organization",
            "number",
            "date",
            "amount",
            "currency",
            "paid_amount",
            "remaining_amount",
            "status",
            "purpose",
            "comment",
            "original_url",
            "public_receipt_url",
            "decision_reason",
            "publish_receipt",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_original_url(self, obj):
        if self.context.get("public") or not obj.original_file:
            return None
        return f"/api/invoices/{obj.id}/original/"

    def get_public_receipt_url(self, obj):
        if obj.publish_receipt and obj.public_file:
            return obj.public_file.url
        return None


class InvoiceCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField(required=False, default="KZT")
    number = serializers.CharField(required=False, allow_blank=True, default="")
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    organization_name = serializers.CharField(max_length=255)
    organization_bin = serializers.CharField(max_length=32)
    organization_kind = serializers.ChoiceField(choices=OrganizationKind.choices, required=False)
    iban = serializers.CharField(max_length=64)
    bank_name = serializers.CharField(required=False, allow_blank=True, default="")
    file = serializers.FileField()
    publish_receipt = serializers.BooleanField(required=False, default=True)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля.")
        return value

    def validate_file(self, value):
        validate_upload(value)
        return value

    def validate(self, attrs):
        card = self.context["card"]
        if card.get("status") not in EXPENSE_CARD_STATUSES:
            raise serializers.ValidationError(
                {"detail": "Счета можно добавлять только для активного или завершённого сбора."}
            )
        available = escrow_available(card)
        if attrs["amount"] > available:
            raise serializers.ValidationError(
                {"amount": f"Сумма превышает доступный эскроу-баланс ({available})."}
            )
        return attrs

    def create(self, validated_data):
        uploaded = validated_data.pop("file")
        return create_invoice(
            self.context["card"],
            validated_data,
            actor=self.context["request"].user,
            uploaded=uploaded,
        )


class InvoiceDecisionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_comment(self, value):
        if self.context.get("comment_required") and not value.strip():
            raise serializers.ValidationError("Комментарий обязателен.")
        return value.strip()


class PayoutSerializer(serializers.ModelSerializer):
    invoice_id = serializers.IntegerField(source="invoice.id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Payout
        fields = (
            "id",
            "card_id",
            "invoice_id",
            "organization_name",
            "amount",
            "currency",
            "status",
            "provider",
            "provider_payout_id",
            "failure_reason",
            "processed_at",
            "created_at",
        )
        read_only_fields = fields


class PayoutCreateSerializer(serializers.Serializer):
    invoice_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    idempotency_key = serializers.CharField(required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

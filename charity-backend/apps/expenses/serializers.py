from decimal import Decimal

from rest_framework import serializers

from apps.common.validators import validate_upload

from .models import Expense, ExpenseStatus


class ExpenseSerializer(serializers.ModelSerializer):
    card_id = serializers.IntegerField(source="card.id", read_only=True)
    document = serializers.FileField(source="document_url", read_only=True)

    class Meta:
        model = Expense
        fields = (
            "id",
            "card_id",
            "date",
            "purpose",
            "amount",
            "comment",
            "document",
            "status",
            "moderator_comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ExpenseCreateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Expense
        fields = ("date", "purpose", "amount", "comment", "file")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля.")
        return value

    def validate_file(self, value):
        validate_upload(value)
        return value

    def validate(self, attrs):
        card = self.context["card"]
        amount = attrs["amount"]
        available = Decimal(str(card.escrow_available))
        if amount > available:
            raise serializers.ValidationError(
                {"amount": f"Сумма превышает доступный эскроу-баланс ({available})."}
            )
        return attrs

    def create(self, validated_data):
        uploaded = validated_data.pop("file", None)
        card = self.context["card"]
        expense = Expense.objects.create(
            card=card,
            date=validated_data["date"],
            purpose=validated_data["purpose"],
            amount=validated_data["amount"],
            comment=validated_data.get("comment", ""),
            status=ExpenseStatus.PENDING,
        )
        if uploaded:
            expense.document_url = uploaded
            expense.save(update_fields=["document_url", "updated_at"])
        return expense


class ExpenseModerationSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_comment(self, value):
        if self.context.get("comment_required") and not value.strip():
            raise serializers.ValidationError("Комментарий обязателен.")
        return value.strip()


class ModerationExpenseListSerializer(ExpenseSerializer):
    card_name = serializers.CharField(source="card.full_name", read_only=True)

    class Meta(ExpenseSerializer.Meta):
        fields = ExpenseSerializer.Meta.fields + ("card_name",)
        read_only_fields = fields

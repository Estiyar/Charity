from rest_framework import serializers

from ekomek_common.validators import validate_upload

from .masking import mask_sensitive_text
from .models import Expense, ExpenseCategory, ExpenseDecisionEvent
from .workflow import create_expense, escrow_available


class ExpenseSerializer(serializers.ModelSerializer):
    document = serializers.SerializerMethodField()
    original_url = serializers.SerializerMethodField()
    public_receipt_url = serializers.SerializerMethodField()
    description = serializers.ReadOnlyField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = (
            "id",
            "card_id",
            "card_name",
            "date",
            "category",
            "purpose",
            "description",
            "amount",
            "comment",
            "document",
            "original_url",
            "public_receipt_url",
            "status",
            "submitted_by_id",
            "submitted_at",
            "reviewed_by_id",
            "reviewed_at",
            "decision_reason",
            "moderator_comment",
            "publish_receipt",
            "payout_id",
            "comments",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_document(self, obj):
        if self.context.get("public"):
            return obj.public_file.url if obj.publish_receipt and obj.public_file else None
        return f"/api/expenses/{obj.id}/original/" if obj.original_file else None

    def get_original_url(self, obj):
        if self.context.get("public") or not obj.original_file:
            return None
        return f"/api/expenses/{obj.id}/original/"

    def get_public_receipt_url(self, obj):
        if obj.publish_receipt and obj.public_file:
            return obj.public_file.url
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.context.get("public"):
            return data
        data["purpose"] = mask_sensitive_text(instance.purpose)
        data["comment"] = None
        data["moderator_comment"] = None
        data["decision_reason"] = None
        data["original_url"] = None
        data["payout_id"] = None
        data["comments"] = []
        return data

    def get_comments(self, obj):
        if self.context.get("public"):
            return []
        from .comment_services import serialize_expense_comments

        return serialize_expense_comments(
            obj,
            user=self.context.get("request") and self.context["request"].user,
            include_internal=self.context.get("include_internal", False),
        )


class PublicExpenseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    category = serializers.CharField()
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    status = serializers.CharField()
    public_receipt_url = serializers.CharField(allow_null=True)
    purpose = serializers.CharField(allow_null=True)


class ExpenseCreateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    submit = serializers.BooleanField(write_only=True, required=False, default=True)
    category = serializers.ChoiceField(choices=ExpenseCategory.choices, required=False)

    class Meta:
        model = Expense
        fields = ("date", "purpose", "amount", "comment", "file", "category", "submit", "publish_receipt")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля.")
        return value

    def validate_file(self, value):
        validate_upload(value)
        return value

    def validate(self, attrs):
        if attrs.get("submit", True):
            card = self.context["card"]
            available = escrow_available(card)
            if attrs["amount"] > available:
                raise serializers.ValidationError(
                    {"amount": f"Сумма превышает доступный эскроу-баланс ({available})."}
                )
        return attrs

    def create(self, validated_data):
        uploaded = validated_data.pop("file", None)
        submit = validated_data.pop("submit", True)
        return create_expense(
            self.context["card"],
            validated_data,
            actor=self.context["request"].user,
            uploaded=uploaded,
            submit=submit,
        )


class ExpenseUpdateSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    category = serializers.ChoiceField(choices=ExpenseCategory.choices, required=False)

    class Meta:
        model = Expense
        fields = ("date", "purpose", "amount", "comment", "file", "category", "publish_receipt")
        extra_kwargs = {
            "date": {"required": False},
            "purpose": {"required": False},
            "amount": {"required": False},
            "comment": {"required": False},
            "publish_receipt": {"required": False},
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля.")
        return value

    def validate_file(self, value):
        validate_upload(value)
        return value


class ExpenseModerationSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    revision_comment = serializers.CharField(required=False, allow_blank=True, default="")
    internal_comment = serializers.CharField(required=False, allow_blank=True, default="")
    publish_receipt = serializers.BooleanField(required=False)

    def validate(self, attrs):
        from ekomek_common.comments import resolve_revision_comment

        revision, internal = resolve_revision_comment(attrs)
        if self.context.get("comment_required") and not revision:
            raise serializers.ValidationError({"revision_comment": "Комментарий для автора обязателен."})
        attrs["revision_comment"] = revision
        attrs["internal_comment"] = internal
        attrs["comment"] = revision
        return attrs


class ModerationExpenseListSerializer(ExpenseSerializer):
    class Meta(ExpenseSerializer.Meta):
        fields = ExpenseSerializer.Meta.fields


class AdminExpenseSerializer(ExpenseSerializer):
    class Meta(ExpenseSerializer.Meta):
        fields = ("id", "card_id", "card_name", "date", "purpose", "category", "amount", "status", "created_at")


class ExpenseDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseDecisionEvent
        fields = ("id", "action", "reason", "actor_id", "actor_role", "created_at")
        read_only_fields = fields

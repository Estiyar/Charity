from rest_framework import serializers

from apps.common.card_status import CardStatus
from apps.common.validators import validate_upload

from .models import FundraisingCard, Gender


class CardPublicSerializer(serializers.ModelSerializer):
    contact_phone = serializers.CharField(source="masked_phone", read_only=True)
    progress_percent = serializers.ReadOnlyField()
    escrow_received = serializers.ReadOnlyField()
    escrow_spent = serializers.ReadOnlyField()
    escrow_pending = serializers.ReadOnlyField()
    escrow_available = serializers.ReadOnlyField()
    escrow_balance = serializers.ReadOnlyField()

    class Meta:
        model = FundraisingCard
        fields = (
            "id",
            "full_name",
            "diagnosis",
            "city",
            "clinic",
            "age",
            "gender",
            "description",
            "photo_url",
            "target_amount",
            "collected_amount",
            "end_date",
            "status",
            "iin_masked",
            "document_number_masked",
            "contact_phone",
            "progress_percent",
            "escrow_received",
            "escrow_spent",
            "escrow_pending",
            "escrow_available",
            "escrow_balance",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CardPrivateSerializer(serializers.ModelSerializer):
    iin = serializers.CharField(source="iin_encrypted", read_only=True)
    document_number = serializers.CharField(
        source="document_number_encrypted",
        read_only=True,
    )
    author_id = serializers.IntegerField(source="author.id", read_only=True)
    author_email = serializers.EmailField(source="author.email", read_only=True)
    progress_percent = serializers.ReadOnlyField()
    escrow_received = serializers.ReadOnlyField()
    escrow_spent = serializers.ReadOnlyField()
    escrow_pending = serializers.ReadOnlyField()
    escrow_available = serializers.ReadOnlyField()
    escrow_balance = serializers.ReadOnlyField()

    class Meta:
        model = FundraisingCard
        fields = (
            "id",
            "author_id",
            "author_email",
            "full_name",
            "diagnosis",
            "city",
            "clinic",
            "age",
            "gender",
            "description",
            "photo_url",
            "target_amount",
            "collected_amount",
            "end_date",
            "status",
            "iin",
            "document_number",
            "contact_phone",
            "contact_email",
            "moderator_comment",
            "progress_percent",
            "escrow_received",
            "escrow_spent",
            "escrow_pending",
            "escrow_available",
            "escrow_balance",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


EDITABLE_STATUSES = {CardStatus.DRAFT, CardStatus.REVISION_REQUIRED}


class ConsentBooleanField(serializers.BooleanField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            return data.lower() in ("true", "1", "yes", "on")
        return super().to_internal_value(data)


class OptionalIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if data in (None, ""):
            return None
        return super().to_internal_value(data)


class CardWriteSerializer(serializers.ModelSerializer):
    iin = serializers.CharField(required=False, allow_blank=True)
    document_number = serializers.CharField(required=False, allow_blank=True)
    clinic = serializers.CharField(required=False, allow_blank=True)
    age = OptionalIntegerField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=Gender.choices, required=False, allow_blank=True)
    contact_phone = serializers.CharField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    photo_url = serializers.FileField(required=False, allow_null=True)
    personal_data_consent = ConsentBooleanField(write_only=True, required=False)

    class Meta:
        model = FundraisingCard
        fields = (
            "full_name",
            "diagnosis",
            "city",
            "clinic",
            "age",
            "gender",
            "description",
            "photo_url",
            "target_amount",
            "end_date",
            "iin",
            "document_number",
            "contact_phone",
            "contact_email",
            "personal_data_consent",
        )

    def validate_photo_url(self, value):
        if value:
            validate_upload(value)
        return value

    def validate_personal_data_consent(self, value):
        if self.instance is not None:
            return value
        if value is False:
            raise serializers.ValidationError(
                "Необходимо согласие на обработку персональных данных."
            )
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("personal_data_consent"):
            raise serializers.ValidationError(
                {"personal_data_consent": "Необходимо согласие на обработку персональных данных."}
            )
        if self.instance is not None:
            attrs.pop("personal_data_consent", None)
        if self.instance and self.instance.status not in EDITABLE_STATUSES:
            raise serializers.ValidationError(
                "Редактировать можно только черновик или карточку на доработке."
            )
        return attrs

    def _apply_confidential_fields(self, validated_data):
        iin = validated_data.pop("iin", None)
        document_number = validated_data.pop("document_number", None)
        validated_data.pop("personal_data_consent", None)
        if iin is not None:
            validated_data["iin_encrypted"] = iin
        if document_number is not None:
            validated_data["document_number_encrypted"] = document_number
        return validated_data

    def create(self, validated_data):
        validated_data = self._apply_confidential_fields(validated_data)
        validated_data["author"] = self.context["request"].user
        return FundraisingCard.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_confidential_fields(validated_data)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

from rest_framework import serializers

from apps.common.card_status import CardStatus
from apps.common.validators import validate_iin, validate_upload
from apps.donations.services import is_own_fundraiser

from .models import FundraisingCard, Gender
from .services import FundraiserCreationError, prepare_fundraiser_data


class CardPublicSerializer(serializers.ModelSerializer):
    contact_phone = serializers.CharField(source="masked_phone", read_only=True)
    progress_percent = serializers.ReadOnlyField()
    escrow_received = serializers.ReadOnlyField()
    escrow_spent = serializers.ReadOnlyField()
    escrow_pending = serializers.ReadOnlyField()
    escrow_available = serializers.ReadOnlyField()
    escrow_balance = serializers.ReadOnlyField()
    can_donate = serializers.SerializerMethodField()

    def get_can_donate(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return True
        return not is_own_fundraiser(request.user, obj)

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
            "can_donate",
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
    can_donate = serializers.SerializerMethodField()

    def get_can_donate(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return True
        return not is_own_fundraiser(request.user, obj)

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
            "recipient_iin",
            "is_self",
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
            "can_donate",
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
    recipient_iin = serializers.CharField(required=False, allow_blank=True)
    iin = serializers.CharField(required=False, allow_blank=True)
    document_number = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    diagnosis = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
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
            "recipient_iin",
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
        if self.instance is None:
            recipient_iin = attrs.get("recipient_iin") or attrs.get("iin")
            if not recipient_iin:
                raise serializers.ValidationError(
                    {"recipient_iin": "ИИН получателя обязателен."}
                )
            validate_iin(recipient_iin)
            attrs["recipient_iin"] = recipient_iin
        return attrs

    def _apply_confidential_fields(self, validated_data):
        document_number = validated_data.pop("document_number", None)
        validated_data.pop("personal_data_consent", None)
        validated_data.pop("recipient_iin", None)
        validated_data.pop("iin", None)
        if document_number is not None:
            validated_data["document_number_encrypted"] = document_number
        return validated_data

    def create(self, validated_data):
        author = self.context["request"].user
        document_number = validated_data.pop("document_number", None)
        validated_data.pop("personal_data_consent", None)
        validated_data.pop("iin", None)
        try:
            validated_data = prepare_fundraiser_data(author, validated_data)
        except FundraiserCreationError as exc:
            raise serializers.ValidationError(exc.errors) from exc
        if document_number is not None:
            validated_data["document_number_encrypted"] = document_number
        validated_data["author"] = author
        return FundraisingCard.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_confidential_fields(validated_data)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

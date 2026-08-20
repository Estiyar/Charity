from rest_framework import serializers

from ekomek_common.audit import reveal_encrypted
from ekomek_common.constants import CardStatus, EDITABLE_CARD_STATUSES
from ekomek_common.validators import validate_upload

from .models import FundraisingCard, Gender
from .services import (
    FundraiserCreationError,
    apply_protected_contacts,
    create_card,
    is_own_fundraiser,
    prepare_fundraiser_data,
)


class TrustStatusMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("include_trust"):
            from .trust_services import build_trust_status

            data["trust_status"] = build_trust_status(instance)
        return data


class CardPublicSerializer(TrustStatusMixin, serializers.ModelSerializer):
    contact_phone = serializers.CharField(source="contact_phone_masked", read_only=True)
    progress_percent = serializers.ReadOnlyField()
    escrow_received = serializers.ReadOnlyField()
    escrow_spent = serializers.ReadOnlyField()
    escrow_pending = serializers.ReadOnlyField()
    escrow_available = serializers.ReadOnlyField()
    escrow_balance = serializers.ReadOnlyField()
    can_donate = serializers.SerializerMethodField()

    def get_can_donate(self, obj):
        if obj.status != CardStatus.ACTIVE:
            return False
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


class CardAuthorSerializer(TrustStatusMixin, serializers.ModelSerializer):
    contact_phone = serializers.CharField(source="contact_phone_masked", read_only=True)
    author_id = serializers.IntegerField(read_only=True)
    author_email = serializers.EmailField(read_only=True)
    progress_percent = serializers.ReadOnlyField()
    escrow_received = serializers.ReadOnlyField()
    escrow_spent = serializers.ReadOnlyField()
    escrow_pending = serializers.ReadOnlyField()
    escrow_available = serializers.ReadOnlyField()
    escrow_balance = serializers.ReadOnlyField()
    can_donate = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    def get_can_donate(self, obj):
        if obj.status != CardStatus.ACTIVE:
            return False
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
            "author_full_name",
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
            "is_self",
            "beneficiary_id",
            "representation_id",
            "relationship_type",
            "high_risk",
            "review_reasons",
            "medical_source",
            "iin_masked",
            "document_number_masked",
            "contact_phone",
            "contact_email",
            "moderator_comment",
            "suspend_reason",
            "report_risk_score",
            "unique_report_count",
            "needs_extra_review",
            "duplicate_suspected",
            "progress_percent",
            "escrow_received",
            "escrow_spent",
            "escrow_pending",
            "escrow_available",
            "escrow_balance",
            "can_donate",
            "comments",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_comments(self, obj):
        from .comment_services import serialize_card_comments

        return serialize_card_comments(obj, user=self.context.get("request") and self.context["request"].user)


class CardStaffSerializer(CardAuthorSerializer):
    iin = serializers.SerializerMethodField()
    document_number = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()

    class Meta(CardAuthorSerializer.Meta):
        fields = CardAuthorSerializer.Meta.fields + (
            "iin",
            "document_number",
            "duplicate_signals",
            "duplicate_matches",
            "duplicate_override",
            "duplicate_risk_delta",
        )

    def get_comments(self, obj):
        from .comment_services import serialize_card_comments

        return serialize_card_comments(obj, include_internal=True)

    def _reveal(self, token, field_name):
        obj = self.instance if not isinstance(self.instance, list) else None
        resource = getattr(self, "_current_obj", obj)
        return reveal_encrypted(
            token,
            resource_type="card",
            resource_id=resource.pk,
            field_name=field_name,
            purpose="staff_review",
            request=self.context.get("request"),
        )

    def to_representation(self, instance):
        self._current_obj = instance
        return super().to_representation(instance)

    def get_iin(self, obj):
        return self._reveal(obj.iin_encrypted, "iin")

    def get_document_number(self, obj):
        return self._reveal(obj.document_number_encrypted, "document_number")

    def get_contact_phone(self, obj):
        return self._reveal(obj.contact_phone_encrypted, "contact_phone")


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
    recipient_session_token = serializers.CharField(write_only=True, required=False)
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
            "recipient_session_token",
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
            "document_number",
            "contact_phone",
            "contact_email",
            "personal_data_consent",
        )

    def validate_photo_url(self, value):
        if value:
            validate_upload(value)
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("personal_data_consent"):
            raise serializers.ValidationError(
                {"personal_data_consent": "Необходимо согласие на обработку персональных данных."}
            )
        if self.instance is not None:
            attrs.pop("personal_data_consent", None)
        if self.instance and self.instance.status not in EDITABLE_CARD_STATUSES | {CardStatus.ACTIVE}:
            raise serializers.ValidationError(
                "Редактировать можно только черновик, карточку на доработке или активный сбор."
            )
        if self.instance is None and not attrs.get("recipient_session_token"):
            raise serializers.ValidationError(
                {"recipient_session_token": "Сначала подтвердите получателя."}
            )
        return attrs

    def create(self, validated_data):
        author = self.context["request"].user
        validated_data.pop("personal_data_consent", None)
        try:
            validated_data = prepare_fundraiser_data(author, validated_data)
        except FundraiserCreationError as exc:
            raise serializers.ValidationError(exc.errors) from exc
        return create_card(author, validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("personal_data_consent", None)
        validated_data.pop("recipient_session_token", None)
        if instance.beneficiary_id:
            for field in ("full_name", "age", "gender"):
                validated_data.pop(field, None)
        apply_protected_contacts(validated_data)
        from .history_services import apply_card_field_updates

        return apply_card_field_updates(
            instance,
            validated_data,
            actor=self.context.get("request") and self.context["request"].user,
        )


class AdminCardSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author_full_name", read_only=True)

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
    status = serializers.ChoiceField(choices=CardStatus.ALL)


class InternalCardSerializer(CardAuthorSerializer):
    class Meta(CardAuthorSerializer.Meta):
        fields = CardAuthorSerializer.Meta.fields + (
            "iin_hash",
            "duplicate_signals",
            "duplicate_matches",
            "duplicate_override",
            "duplicate_risk_delta",
        )

    def get_comments(self, obj):
        from .comment_services import serialize_card_comments

        return serialize_card_comments(obj, include_internal=True)

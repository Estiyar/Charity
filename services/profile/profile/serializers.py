import json

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from ekomek_common.audit import reveal_encrypted
from ekomek_common.validators import validate_upload

from .models import Profile
from .privacy import (
    ECP_LOCKED_FIELDS,
    OWNER_EDITABLE_FIELDS,
    age_from_birth_date,
    is_field_locked,
    sanitize_public_fields,
)


def validate_phone_value(value):
    digits = "".join(character for character in (value or "") if character.isdigit())
    if value and len(digits) < 10:
        raise serializers.ValidationError("Укажите корректный номер телефона.")
    return value


class PublicProfileSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "user_id",
            "full_name",
            "avatar",
            "bio",
            "city",
            "role",
            "age",
            "birth_date",
            "email",
            "phone",
            "ecp_status",
        )
        read_only_fields = fields

    def get_age(self, obj):
        return age_from_birth_date(obj.birth_date)

    def get_phone(self, obj):
        return obj.phone_masked if "phone" in (obj.public_fields or []) else None

    def get_email(self, obj):
        return obj.email if "email" in (obj.public_fields or []) else None

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        return obj.avatar.url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        allowed = set(instance.public_fields or [])
        for field in list(data.keys()):
            if field == "user_id":
                continue
            if field == "avatar" and "avatar" not in allowed:
                data[field] = None
            elif field not in allowed and field != "avatar":
                data[field] = None
        return data


class OwnerProfileSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    age = serializers.SerializerMethodField()
    public_fields = serializers.JSONField(required=False)
    locked_fields = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "user_id",
            "full_name",
            "email",
            "role",
            "bio",
            "city",
            "birth_date",
            "age",
            "phone",
            "phone_masked",
            "avatar",
            "verification_status",
            "ecp_status",
            "ecp_locked_fields",
            "iin_masked",
            "public_fields",
            "locked_fields",
            "registered_at",
            "last_login_at",
            "created_at",
        )
        read_only_fields = (
            "user_id",
            "email",
            "role",
            "phone_masked",
            "verification_status",
            "ecp_status",
            "ecp_locked_fields",
            "iin_masked",
            "locked_fields",
            "registered_at",
            "last_login_at",
            "created_at",
            "age",
        )

    def get_age(self, obj):
        return age_from_birth_date(obj.birth_date)

    def get_locked_fields(self, obj):
        return [field for field in ECP_LOCKED_FIELDS if is_field_locked(obj, field)]

    def validate_phone(self, value):
        return validate_phone_value(value)

    def validate_avatar(self, value):
        if not value:
            return value
        try:
            validate_upload(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate_public_fields(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise serializers.ValidationError("Некорректный список публичных полей.") from exc
        return sanitize_public_fields(value)

    def validate_bio(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError("Описание не должно превышать 2000 символов.")
        return value

    def validate(self, attrs):
        profile = self.instance
        if profile is None:
            return attrs
        for field in ECP_LOCKED_FIELDS:
            if field in attrs and is_field_locked(profile, field):
                raise serializers.ValidationError(
                    {field: "Поле получено из ЭЦП и меняется только повторной проверкой или администратором."}
                )
        unknown = set(attrs) - set(OWNER_EDITABLE_FIELDS) - set(ECP_LOCKED_FIELDS)
        for field in list(unknown):
            attrs.pop(field, None)
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["phone"] = instance.decrypted_phone() or instance.phone_masked
        return data

    def update(self, instance, validated_data):
        from .services import apply_owner_updates

        return apply_owner_updates(instance, validated_data)


class StaffProfileSerializer(OwnerProfileSerializer):
    phone = serializers.SerializerMethodField()

    class Meta(OwnerProfileSerializer.Meta):
        read_only_fields = OwnerProfileSerializer.Meta.read_only_fields

    def get_phone(self, obj):
        request = self.context.get("request")
        return reveal_encrypted(
            obj.phone_encrypted,
            resource_type="profile",
            resource_id=obj.user_id,
            field_name="phone",
            purpose="staff_profile_review",
            request=request,
        ) or obj.phone_masked

    def to_representation(self, instance):
        data = super(OwnerProfileSerializer, self).to_representation(instance)
        data["phone"] = self.get_phone(instance)
        data["age"] = age_from_birth_date(instance.birth_date)
        data["locked_fields"] = self.get_locked_fields(instance)
        data["view"] = "staff"
        return data


class AdminProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False)
    birth_date = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    city = serializers.CharField(required=False, allow_blank=True, max_length=128)
    phone = serializers.CharField(required=False, allow_blank=True)
    public_fields = serializers.JSONField(required=False)

    def validate_phone(self, value):
        return validate_phone_value(value)

    def validate_public_fields(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise serializers.ValidationError("Некорректный список публичных полей.") from exc
        return sanitize_public_fields(value)

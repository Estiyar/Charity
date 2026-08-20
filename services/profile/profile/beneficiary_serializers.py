from rest_framework import serializers

from ekomek_common.audit import reveal_encrypted
from ekomek_common.constants import RelationshipType, RepresentationMethod

from .models import Beneficiary, Representation
from .privacy import ALLOWED_BENEFICIARY_PUBLIC_FIELDS


class BeneficiarySerializer(serializers.ModelSerializer):
    medical_linked = serializers.SerializerMethodField()

    class Meta:
        model = Beneficiary
        fields = (
            "id",
            "full_name",
            "birth_date",
            "age",
            "gender",
            "city",
            "clinic",
            "diagnosis",
            "iin_masked",
            "medical_source",
            "medical_linked",
            "verification_status",
            "verified_at",
            "last_checked_at",
            "deceased",
            "closed",
            "public_fields",
            "review_reasons",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_medical_linked(self, obj):
        return bool(obj.medical_source or obj.medical_record_hash)


class PublicBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Beneficiary
        fields = (
            "id",
            "full_name",
            "age",
            "gender",
            "city",
            "clinic",
            "diagnosis",
            "verification_status",
            "deceased",
        )
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        allowed = set(instance.public_fields or [])
        visible = {"id"}
        visible.update(field for field in ALLOWED_BENEFICIARY_PUBLIC_FIELDS if field in allowed)
        if instance.deceased:
            visible.add("deceased")
        return {key: value for key, value in data.items() if key in visible}


class BeneficiaryUpdateSerializer(serializers.Serializer):
    public_fields = serializers.ListField(child=serializers.CharField(), required=False)
    closed = serializers.BooleanField(required=False)
    deceased = serializers.BooleanField(required=False)


class InternalBeneficiarySerializer(BeneficiarySerializer):
    iin = serializers.SerializerMethodField()

    class Meta(BeneficiarySerializer.Meta):
        fields = BeneficiarySerializer.Meta.fields + ("owner_user_id", "iin_hash", "medical_record_hash", "iin")

    def get_iin(self, obj):
        request = self.context.get("request")
        if not request or request.query_params.get("reveal") != "1":
            return None
        return reveal_encrypted(
            obj.iin_encrypted,
            resource_type="beneficiary",
            resource_id=obj.id,
            field_name="iin",
            purpose="card_creation",
            request=request,
            actor_role="internal",
        )


class RepresentationSerializer(serializers.ModelSerializer):
    beneficiary_id = serializers.IntegerField(source="beneficiary.id", read_only=True)
    beneficiary_name = serializers.CharField(source="beneficiary.full_name", read_only=True)

    class Meta:
        model = Representation
        fields = (
            "id",
            "author_id",
            "beneficiary_id",
            "beneficiary_name",
            "relationship_type",
            "verification_method",
            "verification_status",
            "document_ids",
            "verified_at",
            "verified_by",
            "rejection_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RepresentationVerifySerializer(serializers.Serializer):
    representation_id = serializers.IntegerField()
    verification_method = serializers.ChoiceField(choices=RepresentationMethod.ALL)
    document_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class RepresentationRejectSerializer(serializers.Serializer):
    reason = serializers.CharField()


class InternalBeneficiaryUpsertSerializer(serializers.Serializer):
    owner_user_id = serializers.IntegerField()
    iin = serializers.CharField()
    snapshot = serializers.DictField()
    relationship_type = serializers.ChoiceField(choices=RelationshipType.ALL)
    verification_method = serializers.ChoiceField(choices=RepresentationMethod.ALL, required=False)

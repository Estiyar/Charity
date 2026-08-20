from rest_framework import serializers

from ekomek_common.validators import validate_upload

from .masking import mask_iin, public_metadata
from .models import Document, DocumentType, DocumentVisibility, DocumentVersion


class DocumentWriteSerializer(serializers.Serializer):
    file = serializers.FileField()
    document_type = serializers.ChoiceField(choices=DocumentType.choices, required=False)
    issued_at = serializers.DateField(required=False, allow_null=True)
    issuer = serializers.CharField(required=False, allow_blank=True, max_length=255)
    expires_at = serializers.DateField(required=False, allow_null=True)
    supersedes_document_id = serializers.IntegerField(required=False, allow_null=True)
    visibility = serializers.ChoiceField(choices=DocumentVisibility.choices, required=False)
    has_confidential = serializers.BooleanField(required=False)
    metadata = serializers.JSONField(required=False)

    def validate_file(self, value):
        validate_upload(value)
        return value


class DocumentModerationSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    revision_comment = serializers.CharField(required=False, allow_blank=True, default="")
    internal_comment = serializers.CharField(required=False, allow_blank=True, default="")
    has_confidential = serializers.BooleanField(required=False)
    visibility = serializers.ChoiceField(choices=DocumentVisibility.choices, required=False)

    def validate(self, attrs):
        from ekomek_common.comments import resolve_revision_comment

        revision, internal = resolve_revision_comment(attrs)
        if self.context.get("comment_required") and not revision:
            raise serializers.ValidationError({"revision_comment": "Комментарий для автора обязателен."})
        attrs["revision_comment"] = revision
        attrs["internal_comment"] = internal
        attrs["comment"] = revision
        return attrs


def _current(document):
    return document.current_version


class StaffDocumentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()
    verified_at = serializers.SerializerMethodField()
    verified_by = serializers.SerializerMethodField()
    issued_at = serializers.SerializerMethodField()
    issuer = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()
    file_hash = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()
    has_confidential = serializers.SerializerMethodField()
    moderator_comment = serializers.SerializerMethodField()
    version_number = serializers.SerializerMethodField()
    supersedes_document_id = serializers.SerializerMethodField()
    original_url = serializers.SerializerMethodField()
    public_file_url = serializers.SerializerMethodField()
    uploaded_at = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "card_id",
            "document_type",
            "visibility",
            "file_name",
            "file_type",
            "status",
            "verification_status",
            "verified_at",
            "verified_by",
            "issued_at",
            "issuer",
            "expires_at",
            "file_hash",
            "metadata",
            "has_confidential",
            "moderator_comment",
            "version_number",
            "supersedes_document_id",
            "original_url",
            "public_file_url",
            "uploaded_at",
            "comments",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_file_name(self, obj):
        version = _current(obj)
        return version.file_name if version else ""

    def get_file_type(self, obj):
        version = _current(obj)
        return version.file_type if version else ""

    def get_status(self, obj):
        version = _current(obj)
        return version.verification_status if version else ""

    def get_verification_status(self, obj):
        return self.get_status(obj)

    def get_verified_at(self, obj):
        version = _current(obj)
        return version.verified_at if version else None

    def get_verified_by(self, obj):
        version = _current(obj)
        return version.verified_by_id if version else None

    def get_issued_at(self, obj):
        version = _current(obj)
        return version.issued_at if version else None

    def get_issuer(self, obj):
        version = _current(obj)
        return version.issuer if version else ""

    def get_expires_at(self, obj):
        version = _current(obj)
        return version.expires_at if version else None

    def get_file_hash(self, obj):
        version = _current(obj)
        return version.file_hash if version else ""

    def get_metadata(self, obj):
        version = _current(obj)
        return public_metadata(version.metadata) if version else {}

    def get_has_confidential(self, obj):
        version = _current(obj)
        return bool(version.has_confidential) if version else True

    def get_moderator_comment(self, obj):
        version = _current(obj)
        return version.moderator_comment if version else ""

    def get_version_number(self, obj):
        version = _current(obj)
        return version.version_number if version else None

    def get_supersedes_document_id(self, obj):
        version = _current(obj)
        if version is None or version.supersedes_id is None:
            return None
        return obj.id

    def get_original_url(self, obj):
        return f"/api/documents/{obj.id}/original/"

    def get_public_file_url(self, obj):
        version = _current(obj)
        if version is None or not version.public_file:
            return None
        return version.public_file.url

    def get_uploaded_at(self, obj):
        version = _current(obj)
        return version.created_at if version else obj.created_at

    def get_comments(self, obj):
        from ekomek_common.constants import Role

        from .comment_services import serialize_document_comments

        request = self.context.get("request")
        user = getattr(request, "user", None)
        authenticated = getattr(user, "is_authenticated", False)
        include_internal = (not authenticated) or getattr(user, "role", None) in Role.STAFF
        return serialize_document_comments(obj, user=user, include_internal=include_internal)


class PublicDocumentSerializer(serializers.ModelSerializer):
    issued_at = serializers.SerializerMethodField()
    issuer = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()
    verified_at = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()
    public_file_url = serializers.SerializerMethodField()
    uploaded_at = serializers.SerializerMethodField()
    version_number = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "document_type",
            "issued_at",
            "issuer",
            "verification_status",
            "verified_at",
            "expires_at",
            "public_file_url",
            "visibility",
            "uploaded_at",
            "version_number",
        )
        read_only_fields = fields

    def get_issued_at(self, obj):
        version = _current(obj)
        return version.issued_at if version else None

    def get_issuer(self, obj):
        version = _current(obj)
        return mask_iin(version.issuer) if version else ""

    def get_verification_status(self, obj):
        version = _current(obj)
        return version.verification_status if version else ""

    def get_verified_at(self, obj):
        version = _current(obj)
        return version.verified_at if version else None

    def get_expires_at(self, obj):
        version = _current(obj)
        return version.expires_at if version else None

    def get_public_file_url(self, obj):
        version = _current(obj)
        if version is None or not version.public_file:
            return None
        return version.public_file.url

    def get_uploaded_at(self, obj):
        version = _current(obj)
        return version.created_at if version else None

    def get_version_number(self, obj):
        version = _current(obj)
        return version.version_number if version else None


class DocumentVersionSerializer(serializers.ModelSerializer):
    supersedes_version_id = serializers.IntegerField(source="supersedes_id", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = (
            "id",
            "version_number",
            "issued_at",
            "issuer",
            "verification_status",
            "verified_at",
            "verified_by_id",
            "expires_at",
            "supersedes_version_id",
            "file_hash",
            "file_name",
            "file_type",
            "uploaded_by_id",
            "created_at",
        )
        read_only_fields = fields

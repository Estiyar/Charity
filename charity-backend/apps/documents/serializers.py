from rest_framework import serializers

from apps.common.validators import validate_upload

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    card_id = serializers.IntegerField(source="card.id", read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "card_id",
            "file",
            "file_url",
            "file_name",
            "file_type",
            "status",
            "has_confidential",
            "moderator_comment",
            "created_at",
        )
        read_only_fields = (
            "id",
            "card_id",
            "file_url",
            "file_name",
            "file_type",
            "status",
            "moderator_comment",
            "created_at",
        )

    def validate_file(self, value):
        validate_upload(value)
        return value

    def create(self, validated_data):
        uploaded = validated_data.pop("file")
        card = self.context["card"]
        extension = uploaded.name.rsplit(".", 1)[-1].lower()
        document = Document.objects.create(
            card=card,
            file_url=uploaded,
            file_name=uploaded.name,
            file_type=extension,
            has_confidential=validated_data.get("has_confidential", False),
        )
        if extension in ("jpg", "jpeg", "png"):
            card.photo_url = document.file_url
            card.save(update_fields=["photo_url", "updated_at"])
        return document


class DocumentModerationSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    has_confidential = serializers.BooleanField(required=False)

    def validate_comment(self, value):
        if self.context.get("comment_required") and not value.strip():
            raise serializers.ValidationError("Комментарий обязателен.")
        return value.strip()

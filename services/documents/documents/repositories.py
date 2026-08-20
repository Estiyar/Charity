from .models import Document, DocumentStatus, DocumentVersion, DocumentVisibility


class DocumentRepository:
    def for_card(self, card_id):
        return (
            Document.objects.filter(card_id=card_id)
            .select_related("current_version")
            .order_by("-created_at")
        )

    def current_versions(self, card_id=None):
        documents = Document.objects.exclude(current_version=None)
        if card_id is not None:
            documents = documents.filter(card_id=card_id)
        version_ids = documents.values_list("current_version_id", flat=True)
        return DocumentVersion.objects.filter(id__in=version_ids).select_related("document")

    def public_for_card(self, card_id):
        return self.for_card(card_id).filter(
            visibility=DocumentVisibility.PUBLIC,
            current_version__verification_status=DocumentStatus.VERIFIED,
        )

    def pending_review(self):
        return (
            Document.objects.filter(
                current_version__verification_status__in=[DocumentStatus.UPLOADED, DocumentStatus.UNDER_REVIEW]
            )
            .select_related("current_version")
            .order_by("-current_version__created_at")
        )

    def verified_count(self):
        return self.current_versions().filter(verification_status=DocumentStatus.VERIFIED).count()

    def hashes_for_card(self, card_id):
        return list(
            DocumentVersion.objects.filter(document__card_id=card_id)
            .exclude(file_hash="")
            .values_list("file_hash", flat=True)
        )

    def hash_matches(self, hashes, exclude_card_id):
        if not hashes:
            return DocumentVersion.objects.none()
        return (
            DocumentVersion.objects.filter(file_hash__in=hashes)
            .exclude(document__card_id=exclude_card_id)
            .select_related("document")
        )

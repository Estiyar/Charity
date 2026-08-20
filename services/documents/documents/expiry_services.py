from django.utils import timezone

from ekomek_common.outbox import enqueue_event

from .audit_services import record_document_event
from .models import DocumentStatus
from .repositories import DocumentRepository


def expire_due_documents(card_id=None):
    today = timezone.localdate()
    queryset = DocumentRepository().current_versions(card_id).filter(
        expires_at__isnull=False,
        expires_at__lt=today,
        verification_status=DocumentStatus.VERIFIED,
    )
    expired = []
    for version in queryset:
        version.verification_status = DocumentStatus.EXPIRED
        version.save(update_fields=["verification_status", "updated_at"])
        record_document_event(
            version.document,
            "expired",
            version=version,
            payload={"expires_at": str(version.expires_at)},
        )
        enqueue_event(
            "document.expired",
            "document",
            version.document_id,
            {
                "card_id": version.document.card_id,
                "document_id": version.document_id,
                "version_id": version.id,
            },
        )
        expired.append(version)
    return expired

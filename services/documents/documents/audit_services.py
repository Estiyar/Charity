from ekomek_common.audit import actor_from_request

from .masking import public_metadata
from .models import DocumentAuditEvent

EVENT_SUMMARIES = {
    "uploaded": "Загружена новая версия документа",
    "superseded": "Документ заменён новой версией",
    "verified": "Документ подтверждён",
    "rejected": "Документ отклонён",
    "expired": "Срок документа истёк",
    "original_accessed": "Просмотрен оригинал документа",
}


def record_document_event(document, event_type, *, version=None, actor=None, request=None, payload=None):
    actor_id = getattr(actor, "id", None)
    actor_role = getattr(actor, "role", "") or ""
    if request is not None and actor_id is None:
        actor_id, actor_role = actor_from_request(request)
    return DocumentAuditEvent.objects.create(
        document=document,
        version=version,
        event_type=event_type,
        summary=EVENT_SUMMARIES.get(event_type, event_type),
        payload=public_metadata(payload or {}),
        actor_id=actor_id,
        actor_role=actor_role,
    )

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

from ekomek_common.outbox import enqueue_event
from ekomek_common.validators import validate_upload

from .audit_services import record_document_event
from .file_hashes import sha256_uploaded_file
from .models import Document, DocumentStatus, DocumentType, DocumentVersion, DocumentVisibility
from .redaction import build_public_copy


class DuplicateDocumentFile(ValidationError):
    pass


def read_uploaded_bytes(uploaded):
    if hasattr(uploaded, "chunks"):
        payload = b"".join(uploaded.chunks())
    else:
        payload = uploaded.read()
    if hasattr(uploaded, "seek"):
        uploaded.seek(0)
    return payload


def _next_version_number(document):
    latest = document.versions.order_by("-version_number").first()
    return (latest.version_number if latest else 0) + 1


def _ensure_unique_hash(card_id, file_hash):
    if DocumentVersion.objects.filter(document__card_id=card_id, file_hash=file_hash).exists():
        raise DuplicateDocumentFile("Этот файл уже загружен для карточки.")


def _resolve_parent(card_id, supersedes_document_id):
    if not supersedes_document_id:
        return None
    parent = Document.objects.filter(pk=supersedes_document_id, card_id=card_id).first()
    if parent is None:
        raise ValidationError({"supersedes_document_id": "Документ для замены не найден."})
    return parent


@transaction.atomic
def create_document_version(card_id, uploaded, *, actor=None, attrs=None):
    attrs = attrs or {}
    validate_upload(uploaded)
    parent = _resolve_parent(card_id, attrs.get("supersedes_document_id"))
    file_bytes = read_uploaded_bytes(uploaded)
    file_hash = sha256_uploaded_file(ContentFile(file_bytes, name=uploaded.name))
    _ensure_unique_hash(card_id, file_hash)
    document = parent or Document.objects.create(
        card_id=card_id,
        document_type=attrs.get("document_type") or DocumentType.MEDICAL,
        visibility=attrs.get("visibility") or DocumentVisibility.PUBLIC,
    )
    previous = document.current_version
    version = DocumentVersion(
        document=document,
        version_number=_next_version_number(document),
        issued_at=attrs.get("issued_at"),
        issuer=attrs.get("issuer") or "",
        expires_at=attrs.get("expires_at"),
        supersedes=previous,
        file_hash=file_hash,
        metadata=attrs.get("metadata") or {},
        visibility=attrs.get("visibility") or document.visibility,
        file_name=uploaded.name,
        file_type=uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else "",
        has_confidential=bool(attrs.get("has_confidential", True)),
        uploaded_by_id=getattr(actor, "id", None),
        verification_status=DocumentStatus.UPLOADED,
    )
    version.original_file.save(uploaded.name, ContentFile(file_bytes), save=False)
    version.public_file.save(
        f"{version.version_number}.png",
        build_public_copy(version, file_bytes),
        save=False,
    )
    version.save()
    if attrs.get("visibility"):
        document.visibility = attrs["visibility"]
    if attrs.get("document_type") and parent is None:
        document.document_type = attrs["document_type"]
    document.current_version = version
    document.save()
    _record_upload(document, version, previous, actor)
    return document


def _record_upload(document, version, previous, actor):
    record_document_event(
        document,
        "uploaded",
        version=version,
        actor=actor,
        payload={"version_number": version.version_number, "file_name": version.file_name},
    )
    if previous is not None:
        record_document_event(
            document,
            "superseded",
            version=previous,
            actor=actor,
            payload={"replaced_by_version": version.version_number},
        )
    enqueue_event(
        "document.uploaded",
        "document",
        document.id,
        {
            "card_id": document.card_id,
            "document_id": document.id,
            "version_id": version.id,
            "replaced": previous is not None,
        },
    )


def card_allows_upload(card):
    from ekomek_common.constants import DOCUMENT_UPLOAD_STATUSES

    return bool(card) and card.get("status") in DOCUMENT_UPLOAD_STATUSES

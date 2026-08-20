from django.core.exceptions import ValidationError
from django.utils import timezone

from ekomek_common.constants import Role
from ekomek_common.http import ServiceClientError, cards_client
from ekomek_common.outbox import enqueue_event

from .audit_services import record_document_event
from .models import Document, DocumentStatus, DocumentVisibility
from .repositories import DocumentRepository


def fetch_card(card_id):
    try:
        return cards_client().get(f"/internal/cards/{card_id}/")
    except ServiceClientError as exc:
        if exc.status_code == 404:
            return None
        raise


def is_staff(user):
    return getattr(user, "is_authenticated", False) and getattr(user, "role", None) in Role.STAFF


def is_card_author(user, card):
    return (
        getattr(user, "is_authenticated", False)
        and getattr(user, "role", None) == Role.AUTHOR
        and card
        and card.get("author_id") == user.id
    )


def can_manage_documents(user, card):
    return is_staff(user) or is_card_author(user, card)


def can_view_original(user, document):
    if is_staff(user):
        return True
    card = fetch_card(document.card_id)
    return is_card_author(user, card)


def can_view_public_copy(user, document):
    version = document.current_version
    if version is None or not version.public_file:
        return False
    if document.visibility == DocumentVisibility.PUBLIC and version.verification_status == DocumentStatus.VERIFIED:
        return True
    card = fetch_card(document.card_id)
    return can_manage_documents(user, card)


def mark_verified(document, *, actor, comment="", has_confidential=None):
    version = document.current_version
    if version is None:
        raise ValidationError("У документа нет текущей версии.")
    version.verification_status = DocumentStatus.VERIFIED
    version.verified_at = timezone.now()
    version.verified_by_id = getattr(actor, "id", None)
    if has_confidential is not None:
        version.has_confidential = has_confidential
    if comment:
        version.moderator_comment = comment
    version.save()
    record_document_event(document, "verified", version=version, actor=actor, payload={"comment": comment})
    enqueue_event(
        "document.verified",
        "document",
        document.id,
        {"card_id": document.card_id, "document_id": document.id, "version_id": version.id},
    )
    return document


def mark_rejected(document, *, actor, comment):
    version = document.current_version
    if version is None:
        raise ValidationError("У документа нет текущей версии.")
    version.verification_status = DocumentStatus.REJECTED
    version.moderator_comment = comment
    version.save()
    record_document_event(document, "rejected", version=version, actor=actor, payload={"comment": comment})
    enqueue_event(
        "document.rejected",
        "document",
        document.id,
        {"card_id": document.card_id, "document_id": document.id, "version_id": version.id},
    )
    return document


def mark_revision_required(document, *, actor, comment, internal_comment=""):
    if not comment:
        raise ValidationError("Комментарий обязателен при запросе доработки.")
    version = document.current_version
    if version is None:
        raise ValidationError("У документа нет текущей версии.")
    version.verification_status = DocumentStatus.REVISION_REQUIRED
    version.moderator_comment = comment
    version.save()
    from .comment_services import record_document_comments

    record_document_comments(document, revision_body=comment, internal_body=internal_comment, actor=actor)
    record_document_event(
        document,
        "revision_required",
        version=version,
        actor=actor,
        payload={"comment": comment},
    )
    card = fetch_card(document.card_id) or {}
    enqueue_event(
        "document.revision_required",
        "document",
        document.id,
        {
            "card_id": document.card_id,
            "document_id": document.id,
            "version_id": version.id,
            "author_id": card.get("author_id"),
            "revision_comment": comment,
        },
    )
    return document


def duplicate_matches_for_card(card_id):
    repository = DocumentRepository()
    hashes = repository.hashes_for_card(card_id)
    matches = repository.hash_matches(hashes, card_id)
    return [
        {
            "document_id": item.document_id,
            "version_id": item.id,
            "card_id": item.document.card_id,
            "file_hash": item.file_hash,
        }
        for item in matches
    ]

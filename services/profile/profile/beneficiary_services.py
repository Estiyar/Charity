from datetime import date

from django.utils import timezone

from ekomek_common.constants import (
    BeneficiaryStatus,
    RelationshipType,
    RepresentationMethod,
    RepresentationStatus,
)
from ekomek_common.outbox import enqueue_event

from .models import Beneficiary, Representation
from .privacy import default_beneficiary_public_fields, sanitize_beneficiary_public_fields
from .repositories import BeneficiaryRepository, RepresentationRepository


class RepresentationActionError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def age_from_birth_date(birth_date):
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def resolve_beneficiary_status(snapshot):
    if snapshot.get("blocked"):
        return BeneficiaryStatus.MANUAL_REVIEW
    if snapshot.get("requires_manual_review") or snapshot.get("incomplete") or snapshot.get("unavailable"):
        if snapshot.get("found") and not snapshot.get("inconsistent"):
            return BeneficiaryStatus.INCOMPLETE
        return BeneficiaryStatus.MANUAL_REVIEW
    if snapshot.get("found") and snapshot.get("full_name"):
        return BeneficiaryStatus.VERIFIED
    return BeneficiaryStatus.UNVERIFIED


def apply_snapshot(beneficiary, snapshot):
    beneficiary.full_name = snapshot.get("full_name") or beneficiary.full_name
    birth_date = snapshot.get("birth_date")
    if birth_date:
        if isinstance(birth_date, str):
            beneficiary.birth_date = date.fromisoformat(birth_date[:10])
        else:
            beneficiary.birth_date = birth_date
    beneficiary.age = snapshot.get("age") or age_from_birth_date(beneficiary.birth_date)
    beneficiary.gender = snapshot.get("gender") or beneficiary.gender
    beneficiary.city = snapshot.get("city") or beneficiary.city
    beneficiary.clinic = snapshot.get("clinic") or beneficiary.clinic
    beneficiary.diagnosis = snapshot.get("diagnosis") or beneficiary.diagnosis
    beneficiary.medical_source = snapshot.get("source") or beneficiary.medical_source
    beneficiary.medical_record_hash = snapshot.get("iin_hash") or beneficiary.iin_hash or beneficiary.medical_record_hash
    beneficiary.review_reasons = snapshot.get("review_reasons") or []
    beneficiary.verification_status = resolve_beneficiary_status(snapshot)
    beneficiary.last_checked_at = timezone.now()
    if beneficiary.verification_status == BeneficiaryStatus.VERIFIED:
        beneficiary.verified_at = timezone.now()
    return beneficiary


def upsert_beneficiary(owner_user_id, iin, snapshot):
    repository = BeneficiaryRepository()
    from ekomek_common.crypto import hmac_hash

    existing = repository.get_by_owner_and_hash(owner_user_id, hmac_hash(iin))
    created = existing is None
    beneficiary = existing or Beneficiary(owner_user_id=owner_user_id)
    beneficiary.assign_iin(iin)
    apply_snapshot(beneficiary, snapshot)
    if not beneficiary.public_fields:
        beneficiary.public_fields = default_beneficiary_public_fields()
    beneficiary.save()
    event_type = "beneficiary.created" if created else "beneficiary.updated"
    enqueue_event(
        event_type,
        "beneficiary",
        beneficiary.id,
        {
            "beneficiary_id": beneficiary.id,
            "owner_user_id": owner_user_id,
            "iin_hash": beneficiary.iin_hash,
            "status": beneficiary.verification_status,
        },
    )
    return beneficiary, created


def representation_event(event_type, representation, extra=None):
    payload = {
        "representation_id": representation.id,
        "beneficiary_id": representation.beneficiary_id,
        "author_id": representation.author_id,
        "relationship_type": representation.relationship_type,
        "verification_method": representation.verification_method,
        "verification_status": representation.verification_status,
    }
    if extra:
        payload.update(extra)
    enqueue_event(event_type, "representation", representation.id, payload)


def auto_verifies(relationship_type, verification_method):
    if relationship_type == RelationshipType.SELF:
        return True
    return verification_method == RepresentationMethod.ECP


def ensure_representation(author_id, beneficiary, relationship_type, verification_method):
    repository = RepresentationRepository()
    existing = repository.get_for_author_beneficiary(author_id, beneficiary.id)
    method = verification_method or (
        RepresentationMethod.ECP if relationship_type == RelationshipType.SELF else RepresentationMethod.MANUAL_REVIEW
    )
    if existing:
        if existing.verification_status == RepresentationStatus.VERIFIED:
            return existing
        existing.relationship_type = relationship_type or existing.relationship_type
        existing.verification_method = method
        existing.save(update_fields=["relationship_type", "verification_method", "updated_at"])
        if auto_verifies(existing.relationship_type, method):
            return confirm_representation(existing, verified_by=author_id)
        return existing
    status_value = (
        RepresentationStatus.VERIFIED
        if auto_verifies(relationship_type, method)
        else RepresentationStatus.PENDING
    )
    representation = Representation(
        author_id=author_id,
        beneficiary=beneficiary,
        relationship_type=relationship_type,
        verification_method=method,
        verification_status=status_value,
    )
    if status_value == RepresentationStatus.VERIFIED:
        representation.verified_at = timezone.now()
        representation.verified_by = author_id
    representation.save()
    if status_value == RepresentationStatus.VERIFIED:
        representation_event("representation.verified", representation)
    return representation


def submit_representation_verification(representation, method, document_ids=None):
    representation.verification_method = method
    representation.document_ids = document_ids or representation.document_ids or []
    if auto_verifies(representation.relationship_type, method):
        return confirm_representation(representation, verified_by=representation.author_id)
    representation.verification_status = RepresentationStatus.MANUAL_REVIEW
    representation.save(
        update_fields=["verification_method", "document_ids", "verification_status", "updated_at"]
    )
    representation_event("representation.submitted", representation)
    return representation


def confirm_representation(representation, verified_by=None):
    if representation.verification_status == RepresentationStatus.VERIFIED:
        return representation
    representation.verification_status = RepresentationStatus.VERIFIED
    representation.verified_at = timezone.now()
    representation.verified_by = verified_by
    representation.rejection_reason = ""
    representation.save(
        update_fields=["verification_status", "verified_at", "verified_by", "rejection_reason", "updated_at"]
    )
    representation_event("representation.verified", representation)
    return representation


def reject_representation(representation, reason, rejected_by=None):
    if not (reason or "").strip():
        raise RepresentationActionError("Причина отклонения обязательна.")
    if representation.verification_status == RepresentationStatus.VERIFIED:
        raise RepresentationActionError("Подтверждённое представительство нельзя отклонить этим действием.")
    representation.verification_status = RepresentationStatus.REJECTED
    representation.rejection_reason = reason.strip()
    representation.verified_by = rejected_by
    representation.verified_at = timezone.now()
    representation.save(
        update_fields=["verification_status", "rejection_reason", "verified_by", "verified_at", "updated_at"]
    )
    representation_event("representation.rejected", representation, {"reason": representation.rejection_reason})
    return representation


def update_beneficiary_visibility(beneficiary, public_fields=None, closed=None, deceased=None):
    if public_fields is not None:
        beneficiary.public_fields = sanitize_beneficiary_public_fields(public_fields)
    if closed is not None:
        beneficiary.closed = closed
    if deceased is not None:
        beneficiary.deceased = deceased
    beneficiary.save()
    enqueue_event(
        "beneficiary.updated",
        "beneficiary",
        beneficiary.id,
        {
            "beneficiary_id": beneficiary.id,
            "owner_user_id": beneficiary.owner_user_id,
            "public_fields": beneficiary.public_fields,
            "closed": beneficiary.closed,
            "deceased": beneficiary.deceased,
        },
    )
    return beneficiary

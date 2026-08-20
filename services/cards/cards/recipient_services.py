from ekomek_common.constants import RelationshipType, RepresentationMethod
from ekomek_common.http import ServiceClientError, identity_client, profile_client, verification_client
from django.core.exceptions import ValidationError as DjangoValidationError
from ekomek_common.validators import validate_iin

from .recipient_cache import store_recipient_session


class RecipientVerifyError(Exception):
    def __init__(self, message, code="recipient_verify_failed", status_code=400, errors=None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.errors = errors or {"non_field_errors": [message]}
        super().__init__(message)


def relationship_for_kind(kind, relationship_type):
    if kind == "self":
        return RelationshipType.SELF
    if relationship_type in RelationshipType.ALL:
        return relationship_type
    if kind == "child":
        return RelationshipType.PARENT
    return RelationshipType.REPRESENTATIVE


def method_for_payload(kind, data):
    if kind == "self":
        return RepresentationMethod.ECP
    if data.get("cms"):
        return RepresentationMethod.ECP
    if data.get("document_ids"):
        return RepresentationMethod.DOCUMENT
    if data.get("source_iin") or data.get("iin"):
        return RepresentationMethod.EXTERNAL_SOURCE
    return RepresentationMethod.MANUAL_REVIEW


def kind_from_relationship(relationship_type):
    if relationship_type == RelationshipType.SELF:
        return "self"
    if relationship_type in RelationshipType.DEPENDENT:
        return "child"
    return "other"


def _identity_profile(author):
    try:
        return identity_client().get(f"/internal/users/{author.id}/", params={"reveal": "1"})
    except ServiceClientError as exc:
        raise RecipientVerifyError("Не удалось получить данные автора.") from exc


def _consume_challenge(challenge_id):
    try:
        payload = identity_client().post(
            "/internal/ecp/challenges/consume/",
            json={"challenge_id": challenge_id},
        )
    except ServiceClientError as exc:
        raise RecipientVerifyError("Challenge истёк или уже использован.", code="challenge_expired") from exc
    return payload.get("challenge")


def _verify_cms(challenge, cms):
    try:
        return verification_client().post("/internal/ecp/verify/", json={"challenge": challenge, "cms": cms})
    except ServiceClientError as exc:
        detail = (exc.payload or {}).get("detail") or "Не удалось проверить ЭЦП получателя."
        raise RecipientVerifyError(detail, status_code=exc.status_code or 400) from exc


def resolve_recipient_identity(author, data):
    kind = data.get("kind") or "self"
    cms = data.get("cms")
    challenge_id = data.get("challenge_id")
    if kind == "self":
        profile = _identity_profile(author)
        iin = profile.get("iin")
        if not iin:
            raise RecipientVerifyError("У автора нет подтверждённого ИИН. Пройдите регистрацию через ЭЦП.")
        return iin, {"full_name": profile.get("full_name") or author.full_name, "birth_date": profile.get("birth_date")}
    if cms and challenge_id:
        challenge = _consume_challenge(challenge_id)
        verified = _verify_cms(challenge, cms)
        iin = verified.get("iin")
        if not iin:
            raise RecipientVerifyError("ЭЦП не содержит ИИН получателя.")
        return iin, {"full_name": verified.get("full_name") or "", "birth_date": verified.get("birth_date")}
    source_iin = data.get("source_iin") or data.get("iin")
    if not source_iin:
        raise RecipientVerifyError("Подпишите ЭЦП получателя или выполните поиск в официальном источнике.")
    try:
        validate_iin(source_iin)
    except DjangoValidationError as exc:
        raise RecipientVerifyError(exc.messages[0]) from exc
    return source_iin, {"full_name": "", "birth_date": None}


def _verify_medical(iin, identity, author_iin_hash):
    try:
        return verification_client().post(
            "/internal/recipient/verify/",
            json={
                "iin": iin,
                "author_iin_hash": author_iin_hash,
                "full_name": identity.get("full_name") or "",
                "birth_date": identity.get("birth_date"),
            },
        )
    except ServiceClientError as exc:
        raise RecipientVerifyError("Проверка получателя недоступна.", status_code=503) from exc


def _upsert_beneficiary(author_id, iin, snapshot, relationship_type, verification_method):
    try:
        return profile_client().post(
            "/internal/beneficiaries/",
            json={
                "owner_user_id": author_id,
                "iin": iin,
                "snapshot": snapshot,
                "relationship_type": relationship_type,
                "verification_method": verification_method,
            },
        )
    except ServiceClientError as exc:
        detail = (exc.payload or {}).get("detail") or "Не удалось сохранить получателя."
        raise RecipientVerifyError(detail) from exc


def public_recipient_payload(session):
    snapshot = session["snapshot"]
    representation = session["representation"]
    return {
        "beneficiary_id": session["beneficiary_id"],
        "representation_id": session["representation_id"],
        "kind": session["kind"],
        "relationship_type": session["relationship_type"],
        "is_self": snapshot.get("is_self") or session["relationship_type"] == RelationshipType.SELF,
        "full_name": snapshot.get("full_name") or "",
        "birth_date": snapshot.get("birth_date"),
        "age": snapshot.get("age"),
        "gender": snapshot.get("gender") or "",
        "city": snapshot.get("city") or "",
        "clinic": snapshot.get("clinic") or "",
        "diagnosis": snapshot.get("diagnosis") or "",
        "iin_masked": snapshot.get("iin_masked") or "",
        "verification_status": session.get("beneficiary_status") or "",
        "representation_status": representation.get("verification_status") or "",
        "medical_source": snapshot.get("source") or "",
        "incomplete": bool(snapshot.get("incomplete")),
        "high_risk": bool(snapshot.get("high_risk")),
        "requires_manual_review": bool(snapshot.get("requires_manual_review")),
        "review_reasons": snapshot.get("review_reasons") or [],
        "locked_fields": ["full_name", "iin", "birth_date", "age", "gender"],
    }


def snapshot_from_stored(stored, iin):
    return {
        "iin": iin,
        "iin_hash": stored.get("iin_hash"),
        "iin_masked": stored.get("iin_masked"),
        "full_name": stored.get("full_name") or "",
        "birth_date": stored.get("birth_date"),
        "age": stored.get("age"),
        "gender": stored.get("gender") or "",
        "city": stored.get("city") or "",
        "clinic": stored.get("clinic") or "",
        "diagnosis": stored.get("diagnosis") or "",
        "source": stored.get("medical_source") or "",
        "found": bool(stored.get("medical_linked") or stored.get("full_name")),
        "is_self": False,
        "incomplete": False,
        "high_risk": False,
        "requires_manual_review": stored.get("verification_status") == "manual_review",
        "review_reasons": stored.get("review_reasons") or [],
    }


def verify_existing_beneficiary(author, beneficiary_id):
    try:
        stored = profile_client().get(
            f"/internal/beneficiaries/{beneficiary_id}/",
            params={"reveal": "1", "author_id": author.id},
        )
    except ServiceClientError as exc:
        raise RecipientVerifyError("Получатель не найден.") from exc
    if stored.get("owner_user_id") != author.id:
        raise RecipientVerifyError("Нет доступа к этому получателю.")
    iin = stored.get("iin")
    if not iin:
        raise RecipientVerifyError("Не удалось восстановить данные получателя.")
    representation = stored.get("representation")
    if not representation:
        raise RecipientVerifyError("Представительство для этого получателя не найдено.")
    relationship_type = representation.get("relationship_type") or RelationshipType.REPRESENTATIVE
    snapshot = snapshot_from_stored(stored, iin)
    snapshot["is_self"] = relationship_type == RelationshipType.SELF
    session = {
        "kind": kind_from_relationship(relationship_type),
        "relationship_type": relationship_type,
        "iin": iin,
        "iin_hash": stored.get("iin_hash"),
        "snapshot": snapshot,
        "beneficiary_id": stored["id"],
        "representation_id": representation["id"],
        "representation": representation,
        "beneficiary_status": stored.get("verification_status"),
    }
    token, ttl = store_recipient_session(session)
    payload = public_recipient_payload(session)
    payload["recipient_session_token"] = token
    payload["expires_in"] = ttl
    return payload


def verify_recipient_for_author(author, data):
    if data.get("beneficiary_id"):
        return verify_existing_beneficiary(author, data["beneficiary_id"])
    kind = data.get("kind") or "self"
    if kind not in ("self", "child", "other"):
        raise RecipientVerifyError("Укажите тип сбора: self, child или other.")
    relationship_type = relationship_for_kind(kind, data.get("relationship_type"))
    iin, identity = resolve_recipient_identity(author, {**data, "kind": kind})
    snapshot = _verify_medical(iin, identity, getattr(author, "iin_hash", "") or "")
    if snapshot.get("blocked"):
        raise RecipientVerifyError("Высокий уровень риска. Создание сбора невозможно.", errors={"non_field_errors": ["Высокий уровень риска. Создание сбора невозможно."]})
    if kind == "self" and not snapshot.get("is_self"):
        raise RecipientVerifyError("ИИН сертификата не совпадает с автором сбора.")
    stored = _upsert_beneficiary(
        author.id,
        snapshot["iin"],
        snapshot,
        relationship_type,
        method_for_payload(kind, data),
    )
    session = {
        "kind": kind,
        "relationship_type": relationship_type,
        "iin": snapshot["iin"],
        "iin_hash": snapshot.get("iin_hash"),
        "snapshot": snapshot,
        "beneficiary_id": stored["id"],
        "representation_id": stored["representation"]["id"],
        "representation": stored["representation"],
        "beneficiary_status": stored.get("verification_status"),
    }
    token, ttl = store_recipient_session(session)
    payload = public_recipient_payload(session)
    payload["recipient_session_token"] = token
    payload["expires_in"] = ttl
    return payload

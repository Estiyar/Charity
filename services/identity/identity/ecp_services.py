from datetime import date, datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.dateparse import parse_date, parse_datetime

from ekomek_common.constants import Role, UserStatus
from ekomek_common.crypto import hmac_hash
from ekomek_common.http import ServiceClientError, verification_client
from ekomek_common.masking import mask_iin
from ekomek_common.validators import validate_iin

from .ecp import consume_challenge, consume_ecp_session, store_ecp_session
from .models import User
from .repositories import UserRepository
from .services import register_user


class EcpFlowError(Exception):
    def __init__(self, message, code="invalid_ecp", status_code=400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def fetch_antifraud_profile(iin):
    try:
        return verification_client().post("/internal/antifraud/lookup/", json={"iin": iin})
    except ServiceClientError as exc:
        if exc.status_code == 404:
            return None
        raise


def antifraud_is_high(profile):
    if not profile:
        return False
    if profile.get("blocked"):
        return True
    return int(profile.get("risk_score") or 0) >= 70


def resolve_registration_status(role, iin):
    try:
        profile = fetch_antifraud_profile(iin)
        unavailable = False
    except ServiceClientError:
        profile = None
        unavailable = True
    high_risk = antifraud_is_high(profile)
    if role == Role.AUTHOR and (high_risk or unavailable):
        return UserStatus.MANUAL_REVIEW
    return UserStatus.ECP_VERIFIED


def resolve_legacy_status(role, iin):
    try:
        profile = fetch_antifraud_profile(iin)
        unavailable = False
    except ServiceClientError:
        profile = None
        unavailable = True
    high_risk = antifraud_is_high(profile)
    if role == Role.AUTHOR and (high_risk or unavailable):
        return UserStatus.MANUAL_REVIEW
    return UserStatus.UNVERIFIED


def ensure_iin_available(iin):
    validate_iin(iin)
    existing = User.objects.filter(iin_hash=hmac_hash(iin)).first()
    if existing is None:
        return
    if existing.is_blocked:
        raise EcpFlowError("Пользователь с таким ИИН заблокирован.")
    raise EcpFlowError("Пользователь с таким ИИН уже зарегистрирован.")


def parse_birth_date(value):
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return parse_date(str(value)[:10])


def author_is_adult(birth_date):
    if birth_date is None:
        return True
    today = date.today()
    years = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return years >= 18


def public_ecp_payload(session):
    return {
        "full_name": session.get("full_name") or "",
        "iin_masked": session.get("iin_masked") or mask_iin(session.get("iin") or ""),
        "birth_date": session.get("birth_date"),
        "certificate_type": session.get("certificate_type") or "",
        "serial_number": session.get("serial_number") or "",
        "issuer": session.get("issuer") or "",
        "valid_from": session.get("valid_from"),
        "valid_to": session.get("valid_to"),
        "locked_fields": ["full_name", "iin", "birth_date"],
    }


def verify_ecp_signature(challenge_id, cms):
    challenge = consume_challenge(challenge_id)
    if challenge is None:
        raise EcpFlowError("Challenge истёк или уже использован.", code="challenge_expired")
    try:
        payload = verification_client().post(
            "/internal/ecp/verify/",
            json={"challenge": challenge, "cms": cms},
        )
    except ServiceClientError as exc:
        detail = (exc.payload or {}).get("detail") or "Не удалось проверить ЭЦП."
        code = (exc.payload or {}).get("code") or "invalid_ecp"
        status_code = 503 if exc.status_code == 503 else 400
        raise EcpFlowError(detail, code=code, status_code=status_code) from exc
    iin = payload.get("iin")
    try:
        validate_iin(iin)
    except DjangoValidationError as exc:
        raise EcpFlowError(exc.messages[0]) from exc
    ensure_iin_available(iin)
    session = {
        "iin": iin,
        "iin_masked": payload.get("iin_masked") or mask_iin(iin),
        "full_name": payload.get("full_name") or "",
        "birth_date": payload.get("birth_date"),
        "certificate_type": payload.get("certificate_type") or "",
        "serial_number": payload.get("serial_number") or "",
        "issuer": payload.get("issuer") or "",
        "valid_from": payload.get("valid_from"),
        "valid_to": payload.get("valid_to"),
        "verification_id": payload.get("verification_id"),
    }
    token, ttl = store_ecp_session(session)
    response = public_ecp_payload(session)
    response["ecp_session_token"] = token
    response["expires_in"] = ttl
    return response


def register_with_ecp(validated_data):
    session = consume_ecp_session(validated_data.pop("ecp_session_token"))
    if session is None:
        raise EcpFlowError("Сессия ЭЦП истекла. Повторите подпись сертификата.", code="session_expired")
    iin = session["iin"]
    ensure_iin_available(iin)
    if UserRepository().email_exists(validated_data["email"]):
        raise EcpFlowError("Пользователь с таким email уже существует.")
    birth_date = parse_birth_date(session.get("birth_date"))
    if validated_data["role"] == Role.AUTHOR and not author_is_adult(birth_date):
        raise EcpFlowError("Автор сбора должен быть совершеннолетним либо действовать как законный представитель.")
    status_value = resolve_registration_status(validated_data["role"], iin)
    user = User(
        email=validated_data["email"],
        role=validated_data["role"],
        status=status_value,
    )
    user.apply_ecp_profile(
        {
            "full_name": session["full_name"],
            "iin": iin,
            "birth_date": birth_date,
            "certificate_type": session.get("certificate_type"),
            "serial_number": session.get("serial_number"),
            "issuer": session.get("issuer"),
            "valid_to": parse_datetime(session["valid_to"]) if session.get("valid_to") else None,
        },
        session.get("verification_id"),
    )
    user.assign_phone(validated_data.get("phone") or "")
    user.set_password(validated_data["password"])
    user.save()
    return register_user(user)

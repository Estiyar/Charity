from ekomek_common.http import ServiceClientError, identity_client
from ekomek_common.outbox import enqueue_event

from .models import Profile
from .privacy import (
    default_public_fields,
    parse_optional_date,
    parse_optional_datetime,
    resolve_ecp_status,
    sanitize_public_fields,
)


IDENTITY_LOCKED_FIELDS = ("full_name", "birth_date")


def get_or_create_profile(user_id, defaults=None):
    payload = defaults or {}
    if "public_fields" not in payload:
        payload = {**payload, "public_fields": default_public_fields()}
    profile, _created = Profile.objects.get_or_create(user_id=user_id, defaults=payload)
    return profile


def apply_identity_snapshot(profile, payload):
    if not payload:
        return profile
    profile.full_name = payload.get("full_name") or profile.full_name
    profile.email = payload.get("email") or profile.email
    profile.role = payload.get("role") or profile.role
    profile.verification_status = payload.get("status") or profile.verification_status
    profile.ecp_status = resolve_ecp_status(payload)
    profile.ecp_locked_fields = payload.get("ecp_locked_fields") or profile.ecp_locked_fields or []
    profile.iin_masked = payload.get("iin_masked") or profile.iin_masked
    birth_date = parse_optional_date(payload.get("birth_date"))
    if birth_date:
        profile.birth_date = birth_date
    registered_at = parse_optional_datetime(payload.get("created_at"))
    if registered_at:
        profile.registered_at = registered_at
    last_login_at = parse_optional_datetime(payload.get("last_login"))
    if last_login_at:
        profile.last_login_at = last_login_at
    if not profile.phone_masked:
        profile.phone_masked = payload.get("phone") or profile.phone_masked
    if not profile.public_fields:
        profile.public_fields = default_public_fields()
    profile.is_public_phone = "phone" in profile.public_fields
    profile.is_public_email = "email" in profile.public_fields
    return profile


def fetch_identity_user(user_id):
    try:
        return identity_client().get(f"/internal/users/{user_id}/")
    except ServiceClientError:
        return None


def sync_profile(profile, request_user=None):
    payload = fetch_identity_user(profile.user_id)
    if payload is None and request_user is not None and getattr(request_user, "id", None) == profile.user_id:
        payload = {
            "full_name": getattr(request_user, "full_name", ""),
            "email": getattr(request_user, "email", ""),
            "role": getattr(request_user, "role", ""),
            "status": getattr(request_user, "status", ""),
        }
    apply_identity_snapshot(profile, payload)
    profile.save()
    return profile


def load_profile(user_id, request_user=None, defaults=None):
    profile = get_or_create_profile(user_id, defaults)
    return sync_profile(profile, request_user)


def serialize_identity_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def push_identity_corrections(user_id, validated_data):
    identity_fields = {
        field: serialize_identity_value(validated_data[field])
        for field in IDENTITY_LOCKED_FIELDS
        if field in validated_data
    }
    if not identity_fields:
        return
    identity_client().patch(f"/internal/users/{user_id}/", json=identity_fields)


def apply_owner_updates(profile, validated_data):
    raw_phone = validated_data.pop("phone", None)
    public_fields = validated_data.pop("public_fields", None)
    for field, value in validated_data.items():
        setattr(profile, field, value)
    if raw_phone is not None:
        profile.assign_phone(raw_phone)
    if public_fields is not None:
        profile.public_fields = sanitize_public_fields(public_fields)
        profile.is_public_phone = "phone" in profile.public_fields
        profile.is_public_email = "email" in profile.public_fields
    profile.save()
    return profile


def apply_admin_updates(profile, validated_data):
    push_identity_corrections(profile.user_id, validated_data)
    raw_phone = validated_data.pop("phone", None)
    public_fields = validated_data.pop("public_fields", None)
    changed = set(validated_data)
    for field, value in validated_data.items():
        setattr(profile, field, value)
    if raw_phone is not None:
        profile.assign_phone(raw_phone)
        changed.add("phone")
    if public_fields is not None:
        profile.public_fields = sanitize_public_fields(public_fields)
        profile.is_public_phone = "phone" in profile.public_fields
        profile.is_public_email = "email" in profile.public_fields
        changed.add("public_fields")
    profile.save()
    enqueue_event(
        "profile.updated",
        "profile",
        profile.user_id,
        {"user_id": profile.user_id, "actor": "admin", "fields": sorted(changed)},
    )
    return profile


def on_user_registered(payload):
    profile = get_or_create_profile(
        payload["user_id"],
        {
            "full_name": payload.get("full_name", ""),
            "email": payload.get("email", ""),
            "role": payload.get("role", ""),
            "verification_status": payload.get("status", ""),
            "iin_masked": payload.get("iin_masked", ""),
            "ecp_locked_fields": payload.get("ecp_locked_fields") or [],
            "public_fields": default_public_fields(),
        },
    )
    apply_identity_snapshot(profile, payload)
    profile.save()


def on_ecp_verified(payload):
    iin_masked = payload.get("iin_masked") or ""
    user_id = payload.get("user_id")
    profile = None
    if user_id:
        profile = Profile.objects.filter(user_id=user_id).first()
    if profile is None and iin_masked:
        profile = Profile.objects.filter(iin_masked=iin_masked).first()
    if profile is None:
        return
    profile.ecp_status = "verified"
    profile.ecp_locked_fields = ["full_name", "iin", "birth_date"]
    if payload.get("full_name"):
        profile.full_name = payload["full_name"]
    profile.save(update_fields=["ecp_status", "ecp_locked_fields", "full_name", "updated_at"])


EVENT_HANDLERS = {
    "user.registered": on_user_registered,
    "user.updated": on_user_registered,
    "ecp.verified": on_ecp_verified,
}

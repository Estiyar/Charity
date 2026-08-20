from datetime import date, datetime

from django.utils.dateparse import parse_date, parse_datetime

ALLOWED_PUBLIC_FIELDS = (
    "full_name",
    "avatar",
    "bio",
    "city",
    "role",
    "age",
    "birth_date",
    "email",
    "phone",
    "ecp_status",
)
DEFAULT_PUBLIC_FIELDS = ["full_name", "avatar", "role"]
OWNER_EDITABLE_FIELDS = ("bio", "city", "phone", "avatar", "public_fields")
ECP_LOCKED_FIELDS = ("full_name", "birth_date")
ALLOWED_BENEFICIARY_PUBLIC_FIELDS = (
    "full_name",
    "age",
    "city",
    "diagnosis",
    "gender",
    "clinic",
)
DEFAULT_BENEFICIARY_PUBLIC_FIELDS = ["full_name", "age", "city", "diagnosis"]


def sanitize_public_fields(values):
    requested = values if isinstance(values, list) else []
    return [field for field in requested if field in ALLOWED_PUBLIC_FIELDS]


def default_public_fields():
    return list(DEFAULT_PUBLIC_FIELDS)


def sanitize_beneficiary_public_fields(values):
    requested = values if isinstance(values, list) else []
    return [field for field in requested if field in ALLOWED_BENEFICIARY_PUBLIC_FIELDS]


def default_beneficiary_public_fields():
    return list(DEFAULT_BENEFICIARY_PUBLIC_FIELDS)


def age_from_birth_date(birth_date):
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def parse_optional_date(value):
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return parse_date(str(value)[:10])


def parse_optional_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return parse_datetime(str(value))


def resolve_ecp_status(payload):
    if payload.get("ecp_verification_id") or payload.get("status") == "ecp_verified":
        return "verified"
    if payload.get("status") == "manual_review":
        return "manual_review"
    return "unverified"


def is_field_locked(profile, field_name):
    locked = profile.ecp_locked_fields or []
    if field_name == "birth_date" and "birth_date" in locked:
        return True
    if field_name == "full_name" and "full_name" in locked:
        return True
    return False

from datetime import date

from ekomek_common.crypto import hmac_hash
from ekomek_common.masking import mask_iin


GENDER_MAP = {
    "male": "male",
    "m": "male",
    "муж": "male",
    "мужской": "male",
    "female": "female",
    "f": "female",
    "жен": "female",
    "женский": "female",
}


def normalize_name(value):
    return " ".join(str(value or "").upper().split())


def names_conflict(left, right):
    if not left or not right:
        return False
    return normalize_name(left) != normalize_name(right)


def gender_from_value(value):
    if not value:
        return ""
    return GENDER_MAP.get(str(value).strip().lower(), "")


def gender_from_iin(iin):
    if not iin or len(iin) < 7 or not iin[6].isdigit():
        return ""
    return "male" if int(iin[6]) % 2 == 1 else "female"


def age_from_birth_date(birth_date):
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def parse_birth_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    try:
        year, month, day = text.split("-")
        return date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def first_text(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def identity_fields(iin):
    return {
        "iin": iin,
        "iin_hash": hmac_hash(iin) if iin else "",
        "iin_masked": mask_iin(iin) if iin else "",
    }

import re

IIN_PATTERN = re.compile(r"\d{12}")
HIDDEN_METADATA_KEYS = frozenset(
    {
        "iin",
        "cms",
        "phone",
        "iin_encrypted",
        "iin_hash",
        "document_number",
        "document_number_hash",
        "contact_phone",
    }
)


def mask_iin(text):
    if not text:
        return text
    return IIN_PATTERN.sub(lambda match: f"{'*' * 8}{match.group(0)[-4:]}", str(text))


def contains_iin(payload):
    if payload is None:
        return False
    if isinstance(payload, (bytes, bytearray)):
        return bool(IIN_PATTERN.search(payload.decode("utf-8", errors="ignore")))
    if isinstance(payload, dict):
        return any(contains_iin(value) for value in payload.values())
    if isinstance(payload, (list, tuple)):
        return any(contains_iin(value) for value in payload)
    return bool(IIN_PATTERN.search(str(payload)))


def public_metadata(metadata):
    if not isinstance(metadata, dict):
        return {}
    cleaned = {}
    for key, value in metadata.items():
        if key.lower() in HIDDEN_METADATA_KEYS:
            continue
        cleaned[key] = public_metadata(value) if isinstance(value, dict) else mask_iin(value)
    return cleaned

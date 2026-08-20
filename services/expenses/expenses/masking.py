import re

IIN_PATTERN = re.compile(r"\d{12}")
ACCOUNT_PATTERN = re.compile(r"\b\d{16,20}\b")
IBAN_PATTERN = re.compile(r"\bKZ[0-9A-Z]{18}\b", re.IGNORECASE)
HIDDEN_KEYS = frozenset({"iin", "iban", "account", "address", "phone", "cms", "bin"})


def mask_iban(value):
    text = str(value or "").replace(" ", "").upper()
    if len(text) < 8:
        return "****"
    return f"{text[:2]}****{text[-4:]}"


def mask_bin(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) < 4:
        return "****"
    return f"{'*' * 8}{digits[-4:]}"


def mask_sensitive_text(value):
    if value is None:
        return value
    text = str(value)
    text = IBAN_PATTERN.sub(lambda match: mask_iban(match.group(0)), text)
    text = IIN_PATTERN.sub(lambda match: f"{'*' * 8}{match.group(0)[-4:]}", text)
    return ACCOUNT_PATTERN.sub("****", text)


def contains_sensitive(payload):
    if payload is None:
        return False
    if isinstance(payload, (bytes, bytearray)):
        return contains_sensitive(payload.decode("utf-8", errors="ignore"))
    if isinstance(payload, dict):
        return any(key.lower() in HIDDEN_KEYS or contains_sensitive(value) for key, value in payload.items())
    return bool(
        IIN_PATTERN.search(str(payload))
        or ACCOUNT_PATTERN.search(str(payload))
        or IBAN_PATTERN.search(str(payload))
    )

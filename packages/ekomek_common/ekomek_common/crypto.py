import base64
import hashlib
import hmac
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class SensitiveDataConfigError(Exception):
    pass


def _settings_value(name, default=""):
    try:
        from django.conf import settings

        if settings.configured:
            value = getattr(settings, name, None)
            if value:
                return value
    except Exception:
        pass
    return os.environ.get(name, default)


def hmac_pepper():
    pepper = _settings_value("IIN_HMAC_PEPPER")
    if not pepper:
        raise SensitiveDataConfigError("IIN_HMAC_PEPPER is not configured")
    return pepper.encode("utf-8")


def derive_fernet_key(secret):
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def fernet_key():
    raw = _settings_value("SENSITIVE_ENCRYPTION_KEY")
    if not raw:
        raise SensitiveDataConfigError("SENSITIVE_ENCRYPTION_KEY is not configured")
    if isinstance(raw, bytes):
        return raw
    try:
        Fernet(raw.encode("utf-8"))
        return raw.encode("utf-8")
    except (ValueError, TypeError):
        return derive_fernet_key(raw)


def hmac_hash(value):
    if value is None:
        return ""
    normalized = str(value).strip()
    if not normalized:
        return ""
    digest = hmac.new(hmac_pepper(), normalized.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def encrypt_value(value):
    if not value:
        return ""
    token = Fernet(fernet_key()).encrypt(str(value).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(token):
    if not token:
        return ""
    try:
        return Fernet(fernet_key()).decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        logger.warning("sensitive_decrypt_failed")
        raise SensitiveDataConfigError("Unable to decrypt sensitive value") from exc


def protect_identifier(value):
    if not value:
        return {"hash": "", "masked": "", "encrypted": ""}
    from ekomek_common.masking import mask_iin

    return {
        "hash": hmac_hash(value),
        "masked": mask_iin(value),
        "encrypted": encrypt_value(value),
    }


def protect_document_number(value):
    if not value:
        return {"hash": "", "masked": "", "encrypted": ""}
    from ekomek_common.masking import mask_document_number

    return {
        "hash": hmac_hash(value),
        "masked": mask_document_number(value),
        "encrypted": encrypt_value(value),
    }


def protect_phone(value):
    if not value:
        return {"masked": "", "encrypted": ""}
    from ekomek_common.masking import mask_phone

    return {
        "masked": mask_phone(value),
        "encrypted": encrypt_value(value),
    }

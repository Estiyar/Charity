import secrets

from django.conf import settings
from django.core.cache import cache


def recipient_session_ttl():
    return int(getattr(settings, "RECIPIENT_SESSION_TTL_SECONDS", 900))


def store_recipient_session(payload):
    token = secrets.token_urlsafe(24)
    cache.set(f"recipient:{token}", payload, recipient_session_ttl())
    return token, recipient_session_ttl()


def consume_recipient_session(token):
    if not token:
        return None
    key = f"recipient:{token}"
    value = cache.get(key)
    if value is None:
        return None
    cache.delete(key)
    return value

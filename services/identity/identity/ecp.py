import secrets

from django.conf import settings
from django.core.cache import cache


def challenge_ttl():
    return int(getattr(settings, "ECP_CHALLENGE_TTL_SECONDS", 300))


def session_ttl():
    return int(getattr(settings, "ECP_SESSION_TTL_SECONDS", 900))


def issue_challenge():
    challenge_id = secrets.token_urlsafe(16)
    challenge = secrets.token_urlsafe(32)
    cache.set(f"ecp:challenge:{challenge_id}", challenge, challenge_ttl())
    return challenge_id, challenge, challenge_ttl()


def consume_challenge(challenge_id):
    if not challenge_id:
        return None
    key = f"ecp:challenge:{challenge_id}"
    value = cache.get(key)
    if value is None:
        return None
    cache.delete(key)
    return value


def store_ecp_session(payload):
    token = secrets.token_urlsafe(24)
    cache.set(f"ecp:session:{token}", payload, session_ttl())
    return token, session_ttl()


def consume_ecp_session(token):
    if not token:
        return None
    key = f"ecp:session:{token}"
    value = cache.get(key)
    if value is None:
        return None
    cache.delete(key)
    return value

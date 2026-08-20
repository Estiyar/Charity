from ekomek_common.correlation import current_correlation_id, current_request_id
from ekomek_common.crypto import decrypt_value


def actor_from_request(request):
    if request is None:
        return None, ""
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return getattr(user, "id", None), getattr(user, "role", "") or ""
    headers = getattr(request, "headers", {}) or {}
    actor_id = headers.get("X-Actor-Id") or headers.get("x-actor-id")
    actor_role = headers.get("X-Actor-Role") or headers.get("x-actor-role") or ""
    if actor_id:
        try:
            actor_id = int(actor_id)
        except (TypeError, ValueError):
            pass
    return actor_id, actor_role


def log_sensitive_access(
    *,
    resource_type,
    resource_id,
    field_name,
    purpose,
    actor_id=None,
    actor_role="",
    request=None,
):
    from ekomek_common.audit_app.models import SensitiveAccessLog

    if request is not None and actor_id is None:
        actor_id, header_role = actor_from_request(request)
        actor_role = actor_role or header_role
    SensitiveAccessLog.objects.create(
        actor_id=actor_id,
        actor_role=actor_role or "",
        resource_type=resource_type,
        resource_id=str(resource_id),
        field_name=field_name,
        purpose=purpose,
        request_id=current_request_id() or "",
        correlation_id=current_correlation_id() or "",
    )


def reveal_encrypted(
    token,
    *,
    resource_type,
    resource_id,
    field_name,
    purpose,
    request=None,
    actor_id=None,
    actor_role="",
):
    if not token:
        return ""
    value = decrypt_value(token)
    log_sensitive_access(
        resource_type=resource_type,
        resource_id=resource_id,
        field_name=field_name,
        purpose=purpose,
        actor_id=actor_id,
        actor_role=actor_role,
        request=request,
    )
    return value

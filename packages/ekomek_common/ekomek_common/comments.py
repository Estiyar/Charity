from ekomek_common.constants import Role


class CommentType:
    REVISION = "revision_comment"
    INTERNAL = "internal_comment"
    ALL = (REVISION, INTERNAL)


def comment_author_fields(actor=None, **overrides):
    fields = {
        "author_id": getattr(actor, "id", None) or 0,
        "author_role": getattr(actor, "role", "") or "",
        "author_name": getattr(actor, "full_name", "") or getattr(actor, "email", "") or "",
    }
    fields.update({key: value for key, value in overrides.items() if value not in (None, "")})
    return fields


def editor_fields(actor=None):
    return {
        "editor_id": getattr(actor, "id", None) or 0,
        "editor_role": getattr(actor, "role", "") or "",
        "editor_name": getattr(actor, "full_name", "") or getattr(actor, "email", "") or "",
    }


def visible_comment_types(user=None, *, include_internal=False):
    if include_internal:
        return CommentType.ALL
    role = getattr(user, "role", None)
    if role in Role.STAFF:
        return CommentType.ALL
    return (CommentType.REVISION,)


def resolve_revision_comment(data):
    revision = (data.get("revision_comment") or data.get("comment") or "").strip()
    internal = (data.get("internal_comment") or "").strip()
    return revision, internal


class CommentActor:
    def __init__(self, data=None, actor=None):
        data = data or {}
        self.id = data.get("comment_author_id") or getattr(actor, "id", None) or 0
        self.role = data.get("comment_author_role") or getattr(actor, "role", "") or ""
        self.full_name = data.get("comment_author_name") or getattr(actor, "full_name", "") or ""
        self.email = getattr(actor, "email", "") or ""

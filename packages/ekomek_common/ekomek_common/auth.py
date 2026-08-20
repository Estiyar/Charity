from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from ekomek_common.constants import Role, UserStatus


class ServicePrincipal:
    is_active = True
    is_anonymous = False
    is_authenticated = True

    def __init__(self, payload):
        self.id = payload.get("user_id")
        self.pk = self.id
        self.role = payload.get("role")
        self.email = payload.get("email", "")
        self.iin = ""
        token_hash = payload.get("iin_hash") or ""
        legacy_iin = payload.get("iin") or ""
        if token_hash:
            self.iin_hash = token_hash
        elif legacy_iin:
            from ekomek_common.crypto import hmac_hash

            self.iin_hash = hmac_hash(legacy_iin)
        else:
            self.iin_hash = ""
        self.full_name = payload.get("full_name", "")
        self.status = payload.get("status", UserStatus.ACTIVE)
        self.is_staff = self.role in Role.STAFF
        self.is_superuser = self.role == Role.ADMIN

    @property
    def is_blocked(self):
        return self.status == UserStatus.BLOCKED

    @property
    def can_create_public_fundraiser(self):
        return self.role == Role.AUTHOR and self.status in UserStatus.CAN_CREATE_FUNDRAISER

    def __str__(self):
        return self.email or str(self.id)


def make_principal(
    user_id,
    role,
    email="",
    iin_hash="",
    iin="",
    full_name="",
    status=UserStatus.ACTIVE,
):
    if iin and not iin_hash:
        from ekomek_common.crypto import hmac_hash

        iin_hash = hmac_hash(iin)
    return ServicePrincipal(
        {
            "user_id": user_id,
            "role": role,
            "email": email,
            "iin_hash": iin_hash,
            "full_name": full_name,
            "status": status,
        }
    )


class ServiceJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token.get("user_id")
        except TokenError as exc:
            raise InvalidToken("Token contained no recognizable user identification") from exc
        if user_id is None:
            raise InvalidToken("Token contained no recognizable user identification")
        return ServicePrincipal(validated_token)


class IdentityJWTAuthentication(JWTAuthentication):
    pass


class _RolePermission(BasePermission):
    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) in self.allowed_roles
        )


class IsDonor(_RolePermission):
    allowed_roles = (Role.DONOR,)


class IsAuthor(_RolePermission):
    allowed_roles = (Role.AUTHOR,)


class IsModerator(_RolePermission):
    allowed_roles = (Role.MODERATOR,)


class IsAdmin(_RolePermission):
    allowed_roles = (Role.ADMIN,)


class IsModeratorOrAdmin(_RolePermission):
    allowed_roles = Role.STAFF


class IsAuthorRole(IsAuthor):
    pass


class HasInternalToken(BasePermission):
    def has_permission(self, request, view):
        from django.conf import settings

        expected = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")
        received = request.headers.get("X-Internal-Token", "")
        return bool(expected) and received == expected

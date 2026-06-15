from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.users.models import Role


class IsAuthorRole(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == Role.AUTHOR
        )


class IsCardOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id


class IsCardOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.role in (Role.MODERATOR, Role.ADMIN):
            return True
        return obj.author_id == request.user.id


class CanManageCard(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == Role.AUTHOR
        )

    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id

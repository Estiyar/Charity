from rest_framework.permissions import BasePermission

from ekomek_common.constants import Role


class CanManageCard(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == Role.AUTHOR

    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id

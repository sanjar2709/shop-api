from rest_framework import permissions


class IsStaffOrReadOnly(permissions.BasePermission):
    """Anyone can read, only staff can create, update or delete."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)

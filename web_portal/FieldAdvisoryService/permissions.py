from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Only admin users can perform write/delete actions. Others get read-only.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff
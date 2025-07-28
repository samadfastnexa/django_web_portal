from rest_framework import permissions
from rest_framework.permissions import BasePermission

# ✅ Role-based permission check
class HasRolePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.role:
            return False

        required_codename = getattr(view, 'required_permission', None)
        if required_codename:
            return request.user.role.permissions.filter(codename=required_codename).exists()
        
        return True  # Allow if no specific permission is required


# ✅ Allow object owner or admin to access
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user and (
            obj == request.user or request.user.is_staff or request.user.is_superuser
        )

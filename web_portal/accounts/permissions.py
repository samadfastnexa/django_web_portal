from rest_framework import permissions

class HasRolePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.role:
            return False

        required_codename = getattr(view, 'required_permission', None)
        if required_codename:
            return request.user.role.permissions.filter(codename=required_codename).exists()
        
        return True  # Allow access if no specific permission is required

from rest_framework import permissions
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


# ✅ Allow object owner or admin to access
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user and (
            obj == request.user or request.user.is_staff or request.user.is_superuser
        )

class HasRolePermission(BasePermission):
    """
    Custom permission class to enforce role-based access control.
    It maps HTTP methods to Django-style permission codenames
    (add_model, view_model, change_model, delete_model), and checks
    if the user's role has the corresponding permission.
    """

    def has_permission(self, request, view):
        user = request.user

        # ✅ Check if user is authenticated and has a role
        if not user.is_authenticated or not hasattr(user, 'role') or not user.role:
            return False

        # ✅ Map HTTP methods to standard permission actions
        method_action_map = {
            'GET': 'view',
            'POST': 'add',
            'PUT': 'change',
            'PATCH': 'change',
            'DELETE': 'delete'
        }

        action = method_action_map.get(request.method)
        if not action:
            return True  # Allow OPTIONS, HEAD, etc.

        # ✅ Dynamically get the model from the view
        model = getattr(getattr(view, 'queryset', None), 'model', None)

        # Fallback to dynamic queryset if `.queryset` is not set as a class attribute
        if not model and hasattr(view, 'get_queryset'):
            model = getattr(view.get_queryset(), 'model', None)

        if not model:
            raise PermissionDenied("Cannot determine the model to check permissions.")

        # ✅ Build the permission codename (e.g., 'add_user', 'view_order')
        model_name = model.__name__.lower()
        required_codename = f"{action}_{model_name}"

        # ✅ Check if the user's role has this permission
        if user.role.permissions.filter(codename=required_codename).exists():
            return True

        # ❌ Denied
        raise PermissionDenied(f"You do not have permission: '{required_codename}'")
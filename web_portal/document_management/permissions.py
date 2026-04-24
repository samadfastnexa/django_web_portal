from rest_framework import permissions


class CanUploadAttachment(permissions.BasePermission):
    """
    Permission class to check if user can upload attachments.
    Only admins, superusers, or users with 'can_upload_attachment' permission.
    """
    message = "You do not have permission to upload attachments."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers and staff have full access
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Check for specific permission
        return request.user.has_perm('document_management.can_upload_attachment')


class CanViewAttachment(permissions.BasePermission):
    """
    Permission class to check if user can view attachments.
    Must have 'can_view_attachment' permission.
    """
    message = "You do not have permission to view attachments."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers and staff have full access
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Check for specific permission
        return request.user.has_perm('document_management.can_view_attachment')

    def has_object_permission(self, request, view, obj):
        """
        Check if user can access specific attachment.
        Admin/superuser can see all, regular users only see assigned attachments.
        """
        # Superusers and staff can access all
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Regular users can only access attachments assigned to them
        return obj.assigned_users.filter(id=request.user.id).exists()


class CanAssignAttachment(permissions.BasePermission):
    """
    Permission class to check if user can assign attachments to other users.
    Only admins, superusers, or users with 'can_assign_attachment' permission.
    """
    message = "You do not have permission to assign attachments."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers and staff have full access
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Check for specific permission
        return request.user.has_perm('document_management.can_assign_attachment')


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission that allows safe methods (GET, HEAD, OPTIONS) for any authenticated user,
    but only allows unsafe methods (POST, PUT, PATCH, DELETE) for admin users.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for admin/staff
        return request.user.is_superuser or request.user.is_staff


class CanModifyAttachment(permissions.BasePermission):
    """
    Permission to check if user can modify (update/delete) an attachment.
    Only the creator or admin can modify.
    """
    message = "You can only modify attachments you created."

    def has_object_permission(self, request, view, obj):
        # Admins can modify any attachment
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Users can only modify their own uploads
        return obj.created_by == request.user


class AttachmentAccessPermission(permissions.BasePermission):
    """
    Comprehensive permission class for attachment operations.
    Handles both list-level and object-level permissions.
    """
    
    def has_permission(self, request, view):
        """Check list-level permissions."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins have full access
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # For GET/HEAD/OPTIONS - user must have view permission
        if request.method in permissions.SAFE_METHODS:
            return request.user.has_perm('document_management.can_view_attachment')
        
        # For POST - user must have upload permission
        if request.method == 'POST':
            return request.user.has_perm('document_management.can_upload_attachment')
        
        # For PUT/PATCH/DELETE - check in object-level permission
        return True

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions."""
        # Admins have full access
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # For GET/HEAD/OPTIONS - check if attachment is assigned to user
        if request.method in permissions.SAFE_METHODS:
            has_view_perm = request.user.has_perm('document_management.can_view_attachment')
            is_assigned = obj.assigned_users.filter(id=request.user.id).exists()
            return has_view_perm and is_assigned
        
        # For PUT/PATCH/DELETE - only creator can modify (unless admin)
        has_upload_perm = request.user.has_perm('document_management.can_upload_attachment')
        is_creator = obj.created_by == request.user
        return has_upload_perm and is_creator

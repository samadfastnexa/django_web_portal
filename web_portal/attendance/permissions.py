from rest_framework.permissions import BasePermission, SAFE_METHODS

class CanApproveAttendanceRequest(BasePermission):
    """
    Only allow users with 'approve_attendance_request' permission to update status.
    Safe methods (GET, HEAD) are allowed for everyone authenticated.
    """

    def has_permission(self, request, view):
        # Allow GET, POST, etc.
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow safe methods
        if request.method in SAFE_METHODS:
            return True

        # If user is trying to update `status`, check permission
        if 'status' in request.data:
            return request.user.role and request.user.role.permissions.filter(codename='approve_attendance_request').exists()

        return True

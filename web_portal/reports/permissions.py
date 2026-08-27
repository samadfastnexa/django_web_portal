from rest_framework.permissions import BasePermission

from .models import UserReportAccess


class CanAccessReport(BasePermission):
    message = "You do not have access to this report."

    def has_permission(self, request, view):
        # Object-level check is done explicitly in the view once the Report
        # instance has been looked up; this class exists to be checked there.
        return True

    def has_object_permission(self, request, view, report):
        return UserReportAccess.objects.filter(user=request.user, report=report).exists()

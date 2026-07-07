from django.contrib import admin

from web_portal.admin import admin_site
from .models import ActivityLog


@admin.register(ActivityLog, site=admin_site)
class ActivityLogAdmin(admin.ModelAdmin):
    """Read-only view of the request/usage audit trail."""

    list_display = (
        'timestamp', 'username', 'method', 'path',
        'status_code', 'duration_ms', 'view_module', 'ip_address',
    )
    list_filter = ('method', 'status_code', 'is_error', 'timestamp')
    search_fields = ('path', 'username', 'view_module', 'ip_address')
    date_hierarchy = 'timestamp'
    list_per_page = 25
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from django.contrib import admin
from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.db.models import Q
from django.utils.html import format_html

from web_portal.admin import admin_site
from web_portal.admin_filters import TextInputFilter, date_range_filter
from .models import ActivityLog


# ----------------------------------------------------------------------
# Business-module mapping
# ----------------------------------------------------------------------
# Maps a request path to the module name the business uses, so the log can be
# read and filtered by feature instead of by Python module. Ordered
# most-specific -> most-general: the first matching prefix wins, so every row
# is labelled exactly once. Add new features near the top.
MODULE_RULES = (
    ('Login / Auth', ('/api/login', '/api/logout', '/api/token', '/api/forgot-password',
                      '/admin/login', '/admin/logout')),
    ('Sales vs Achievement', ('/api/sap/sales-vs-achievement',)),
    ('Collection vs Achievement', ('/api/analytics/collection', '/api/sap/collection')),
    ('Product Catalog', ('/api/sap/products-catalog', '/api/sap/product')),
    ('Weather', ('/api/weather',)),
    ('Dealer Request', ('/api/field/dealer-requests', '/admin/FieldAdvisoryService/dealerrequest')),
    ('Sales Order', ('/api/field/sales-orders', '/admin/FieldAdvisoryService/salesorder',
                     '/admin/sap-sales-order')),
    ('Farmer Meeting', ('/api/meetings', '/admin/farmerMeetingDataEntry/meeting')),
    ('Field Day', ('/api/field-days', '/admin/farmerMeetingDataEntry/fieldday')),
    ('Field Advisory', ('/api/field/schedule', '/admin/FieldAdvisoryService/meetingschedule')),
    ('Dealers', ('/api/field/dealers', '/admin/FieldAdvisoryService/dealer')),
    ('Farmers', ('/api/farmers', '/admin/farmers')),
    ('Complaints', ('/api/complaints', '/admin/complaints')),
    ('Cart & Orders', ('/api/cart', '/api/orders', '/admin/cart')),
    ('Attendance', ('/api/attendance', '/admin/attendance')),
    ('Crop Management', ('/api/crop', '/admin/crop_manage', '/admin/crop_management')),
    ('Documents', ('/api/document', '/admin/document_management')),
    ('Analytics', ('/api/analytics',)),
    ('SAP Integration', ('/api/sap', '/admin/hana-connect', '/admin/sap-', '/admin/sap_integration')),
    ('Monitoring', ('/admin/monitoring', '/admin/admin/logentry')),
    ('Accounts / Users', ('/api/users', '/api/admin/users', '/api/account', '/admin/accounts')),
    ('Admin (other)', ('/admin',)),
    ('API (other)', ('/api',)),
)

UNMAPPED_MODULE = 'Other'


def resolve_module(path):
    """Return the business module name for a request path."""
    candidate = path or ''
    for label, prefixes in MODULE_RULES:
        if candidate.startswith(prefixes):
            return label
    return UNMAPPED_MODULE


# ----------------------------------------------------------------------
# Reusable filters
# ----------------------------------------------------------------------
class UserSearchFilter(TextInputFilter):
    title = 'user'
    parameter_name = 'user_q'
    input_placeholder = 'name, email or username'

    def filter_queryset(self, queryset, value):
        return queryset.filter(
            Q(username__icontains=value) |
            Q(user__username__icontains=value) |
            Q(user__email__icontains=value) |
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value)
        )


class IPAddressFilter(TextInputFilter):
    title = 'IP address'
    parameter_name = 'ip_q'
    input_placeholder = 'e.g. 203.0.113 or 127.0.0.1'

    def filter_queryset(self, queryset, value):
        # icontains so a partial prefix (a subnet) also matches.
        return queryset.filter(ip_address__icontains=value)


class LogEntryUserFilter(TextInputFilter):
    """LogEntry has no denormalized username column, so search the FK only."""
    title = 'user'
    parameter_name = 'user_q'
    input_placeholder = 'name, email or username'

    def filter_queryset(self, queryset, value):
        return queryset.filter(
            Q(user__username__icontains=value) |
            Q(user__email__icontains=value) |
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value)
        )


class ModuleFilter(admin.SimpleListFilter):
    """
    Filter the log by business module (Login, Weather, Field Day, ...).

    Mirrors resolve_module() exactly: a row matches the selected module's
    prefixes but is excluded if a more specific rule higher up already claims
    it, so the filter always agrees with the Module column.
    """

    title = 'module'
    parameter_name = 'module'

    def lookups(self, request, model_admin):
        return [(label, label) for label, _ in MODULE_RULES]

    def queryset(self, request, queryset):
        selected = self.value()
        if not selected:
            return queryset
        claimed_earlier = []
        for label, prefixes in MODULE_RULES:
            if label == selected:
                matches = Q()
                for prefix in prefixes:
                    matches |= Q(path__startswith=prefix)
                queryset = queryset.filter(matches)
                for prefix in claimed_earlier:
                    queryset = queryset.exclude(path__startswith=prefix)
                return queryset
            claimed_earlier.extend(prefixes)
        return queryset


# ----------------------------------------------------------------------
# Admins
# ----------------------------------------------------------------------
@admin.register(ActivityLog, site=admin_site)
class ActivityLogAdmin(admin.ModelAdmin):
    """Read-only view of the request/usage audit trail."""

    list_display = (
        'timestamp', 'username', 'attempted_identifier', 'module_label', 'method', 'path',
        'status_badge', 'suspicious_badge', 'auth_note', 'duration_ms', 'ip_address', 'view_module',
    )
    list_filter = (
        'is_error',
        'is_suspicious',
        ModuleFilter,
        date_range_filter('timestamp', 'date range'),
        UserSearchFilter,
        IPAddressFilter,
        'method',
        'status_code',
        'auth_outcome',
    )
    search_fields = ('path', 'username', 'view_module', 'ip_address', 'attempted_identifier')
    # No date_hierarchy - see DateRangeFilter's docstring (MySQL CONVERT_TZ).
    list_per_page = 25
    ordering = ('-timestamp',)
    list_select_related = ('user',)

    @admin.display(description='Module')
    def module_label(self, obj):
        """Business-facing feature name derived from the request path."""
        return resolve_module(obj.path)

    @admin.display(description='Status', ordering='status_code')
    def status_badge(self, obj):
        """Colour the HTTP status so crashes stand out at a glance."""
        code = obj.status_code or 0
        if code >= 500:
            bg, fg = '#fee2e2', '#991b1b'      # server error / crash
        elif code >= 400:
            bg, fg = '#ffedd5', '#9a3412'      # client error
        elif code >= 300:
            bg, fg = '#e0e7ff', '#3730a3'
        else:
            bg, fg = '#dcfce7', '#166534'
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:10px;font-weight:600;font-size:12px;">{}</span>',
            bg, fg, code,
        )

    @admin.display(description='Auth', ordering='auth_outcome')
    def auth_note(self, obj):
        """Why a 401/403 happened -- distinguishes an expired session from no login."""
        labels = {
            'no_credentials': 'no token',
            'token_expired': 'expired token',
            'token_invalid': 'invalid token',
        }
        label = labels.get(obj.auth_outcome)
        if not label:
            return ''
        colour = '#9a3412' if obj.auth_outcome == 'token_expired' else '#6b7280'
        return format_html('<span style="color:{};font-weight:600;">{}</span>', colour, label)

    @admin.display(description='Flag', ordering='is_suspicious')
    def suspicious_badge(self, obj):
        """Red badge for blocked scanner probes."""
        if not obj.is_suspicious:
            return ''
        return format_html(
            '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;'
            'border-radius:10px;font-weight:700;font-size:12px;">&#9888; probe</span>'
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogEntry, site=admin_site)
class LogEntryAdmin(admin.ModelAdmin):
    """
    Full, filterable history of admin actions - the same data the dashboard's
    "Recent actions" panel shows, but for every user and without the cut-off.
    """

    list_display = ('action_time', 'user', 'action_badge', 'content_type', 'object_repr', 'readable_change')
    list_filter = (
        'action_flag',
        date_range_filter('action_time', 'date range'),
        LogEntryUserFilter,
        'content_type',
    )
    search_fields = ('object_repr', 'change_message', 'user__username', 'user__email')
    # No date_hierarchy - see DateRangeFilter's docstring (MySQL CONVERT_TZ).
    ordering = ('-action_time',)
    list_per_page = 25
    list_select_related = ('user', 'content_type')

    @admin.display(description='Change')
    def readable_change(self, obj):
        """
        Human-readable summary instead of the raw change_message JSON.
        get_change_message() turns [{"changed": {"fields": ["Company"]}}] into
        "Changed Company." and localises field names.
        """
        try:
            message = obj.get_change_message()
        except Exception:
            message = obj.change_message
        return message or '—'

    @admin.display(description='Action', ordering='action_flag')
    def action_badge(self, obj):
        mapping = {
            ADDITION: ('Added', '#dcfce7', '#166534'),
            CHANGE: ('Changed', '#e0e7ff', '#3730a3'),
            DELETION: ('Deleted', '#fee2e2', '#991b1b'),
        }
        label, bg, fg = mapping.get(obj.action_flag, ('Unknown', '#e5e7eb', '#374151'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:10px;font-weight:600;font-size:12px;">{}</span>',
            bg, fg, label,
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Superusers may prune the audit trail; everyone else is read-only.
        return request.user.is_superuser

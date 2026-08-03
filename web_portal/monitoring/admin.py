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
    ('Leave Requests', ('/api/leave-requests', '/admin/attendance/leaverequest')),
    ('Attendance', ('/api/attendance', '/admin/attendance')),
    ('General Ledger', ('/api/general-ledger',)),
    ('Locations', ('/api/available-locations',)),
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
        'status_badge', 'error_summary', 'suspicious_badge', 'auth_note', 'duration_ms', 'ip_address', 'view_module_label',
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
    search_fields = ('path', 'username', 'view_module', 'ip_address', 'attempted_identifier',
                     'error_detail', 'query_string')
    # Clicking a row opens a read-only detail page showing the full error + query.
    readonly_fields = (
        'timestamp', 'user', 'username', 'method', 'path', 'query_string', 'view_module',
        'status_code', 'duration_ms', 'ip_address', 'is_error', 'is_suspicious',
        'auth_outcome', 'attempted_identifier', 'error_detail',
    )
    # No date_hierarchy - see DateRangeFilter's docstring (MySQL CONVERT_TZ).
    list_per_page = 25
    ordering = ('-timestamp',)
    list_select_related = ('user',)

    # Color theme per module group: (background, text)
    MODULE_COLORS = {
        'Login / Auth':           ('#dbeafe', '#1e40af'),
        'Leave Requests':         ('#fef9c3', '#854d0e'),
        'Attendance':             ('#fef9c3', '#854d0e'),
        'Field Advisory':         ('#dcfce7', '#166534'),
        'Farmer Meeting':         ('#dcfce7', '#166534'),
        'Field Day':              ('#dcfce7', '#166534'),
        'HPM':                    ('#dcfce7', '#166534'),
        'Analytics':              ('#ede9fe', '#5b21b6'),
        'Collection vs Achievement': ('#ede9fe', '#5b21b6'),
        'Sales vs Achievement':   ('#ede9fe', '#5b21b6'),
        'SAP Integration':        ('#f3e8ff', '#6b21a8'),
        'Sales Order':            ('#f3e8ff', '#6b21a8'),
        'Product Catalog':        ('#f3e8ff', '#6b21a8'),
        'Accounts / Users':       ('#e0f2fe', '#0369a1'),
        'Complaints':             ('#fee2e2', '#991b1b'),
        'Dealers':                ('#fff7ed', '#9a3412'),
        'Dealer Request':         ('#fff7ed', '#9a3412'),
        'Cart & Orders':          ('#fce7f3', '#9d174d'),
        'Farmers':                ('#ecfdf5', '#065f46'),
        'Documents':              ('#f0fdf4', '#166534'),
        'Crop Management':        ('#f0fdf4', '#166534'),
        'General Ledger':         ('#f8fafc', '#334155'),
        'Monitoring':             ('#f1f5f9', '#475569'),
        'Admin (other)':          ('#f1f5f9', '#475569'),
        'Other':                  ('#f1f5f9', '#6b7280'),
    }

    # Plain-English labels for Python view module paths
    VIEW_MODULE_LABELS = {
        'attendance.views':                  'Attendance & Leave',
        'analytics.views':                   'Analytics Dashboard',
        'accounts.UserViewSet':              'User Accounts',
        'accounts.views':                    'User Accounts',
        'rest_framework_simplejwt.views':    'Login / Token Auth',
        'farmerMeetingDataEntry.views':      'Field Advisory / Farmer Meeting',
        'FieldAdvisoryService.views':        'Field Advisory Service',
        'farmers.views':                     'Farmers',
        'complaints.views':                  'Complaints',
        'cart.views':                        'Cart & Orders',
        'document_management.views':         'Documents',
        'sap_integration.views':             'SAP Integration',
        'general_ledger.views':              'General Ledger',
        'crop_management.views':             'Crop Management',
        'crop_manage.views':                 'Crop Management',
        'farm.views':                        'Farm Management',
        'preferences.views':                 'Preferences',
        'monitoring.security':               'Security — blocked probe',
        'monitoring.middleware':             'Monitoring',
        'kindwise.views':                    'Kindwise (Crop ID)',
        'farmerMeetingDataEntry.hpm_api':    'HPM Requisition',
    }

    # Plain-English rewrites for common technical error strings
    ERROR_PLAIN_ENGLISH = {
        'Authentication credentials were not provided.': 'Not logged in — no token sent',
        'Token is expired':                              'Session expired — needs re-login',
        'Given token not valid for any token type':      'Invalid or expired token',
        'No active account found with the given credentials': 'Wrong email or password',
        'Overlapping leave exists.':                     'Leave dates overlap with an existing request',
        'Date has wrong format':                         'Date sent in wrong format',
        'Incorrect type. Expected pk value':             'Wrong field type sent by app',
        'This field is required':                        'Required field missing',
        'No policy found in SAP':                        'SAP: policy not found',
        'Date range cannot exceed 12 months':            'Date range too wide — max 12 months',
    }

    @admin.display(description='Module')
    def module_label(self, obj):
        """Colored badge showing business module name."""
        label = resolve_module(obj.path)
        bg, fg = self.MODULE_COLORS.get(label, ('#f1f5f9', '#6b7280'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;'
            'border-radius:10px;font-weight:600;font-size:11px;white-space:nowrap;">{}</span>',
            bg, fg, label,
        )

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

    @admin.display(description='Error', ordering='error_detail')
    def error_summary(self, obj):
        """Plain-English error (full technical detail on hover)."""
        if not obj.error_detail:
            return ''
        full = obj.error_detail
        # Find a plain-English rewrite
        plain = full
        for technical, english in self.ERROR_PLAIN_ENGLISH.items():
            if technical.lower() in full.lower():
                plain = english
                break
        short = (plain[:70] + '…') if len(plain) > 70 else plain
        return format_html(
            '<span title="{}" style="color:#991b1b;font-size:12px;">{}</span>', full, short
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

    @admin.display(description='Handled By', ordering='view_module')
    def view_module_label(self, obj):
        """Plain-English name for the Python view that handled the request."""
        raw = obj.view_module or ''
        label = self.VIEW_MODULE_LABELS.get(raw)
        if label:
            return format_html(
                '<span style="color:#475569;font-size:11px;" title="{}">{}</span>',
                raw, label,
            )
        short = raw.replace('.views', '').replace('.api', '').replace('_', ' ').title()
        return format_html(
            '<span style="color:#94a3b8;font-size:11px;" title="{}">{}</span>',
            raw, short or '—',
        )

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

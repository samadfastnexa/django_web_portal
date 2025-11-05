from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import redirect
from .models import Policy
from .sap_client import SAPClient
import datetime


def _parse_date(val):
    if not val:
        return None
    # Accept ISO strings with or without time component
    try:
        if isinstance(val, str):
            # Trim time part if present
            date_part = val.split('T')[0]
            return datetime.date.fromisoformat(date_part)
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.date() if isinstance(val, datetime.datetime) else val
    except Exception:
        return None
    return None


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'policy', 'active', 'valid_from', 'valid_to', 'updated_at')
    list_filter = ('active',)
    search_fields = ('code', 'name', 'policy')
    actions = ['sync_policies_from_sap']
    change_list_template = 'admin/sap_integration/policy/change_list.html'
    readonly_fields = ('code', 'name', 'policy', 'valid_from', 'valid_to', 'active', 'created_at', 'updated_at')

    def sync_policies_from_sap(self, request, queryset):
        """Admin action: Sync policies from SAP Projects (UDF U_pol)."""
        client = SAPClient()
        try:
            data = client.get_all_policies()
        except Exception as e:
            self.message_user(request, _(f"SAP error: {e}"), level='error')
            return

        created = 0
        updated = 0

        for row in data:
            code = row.get('code')
            defaults = {
                'name': row.get('name') or '',
                'policy': row.get('policy') or '',
                'valid_from': _parse_date(row.get('valid_from')),
                'valid_to': _parse_date(row.get('valid_to')),
                'active': bool(row.get('active')),
            }
            obj, is_created = Policy.objects.update_or_create(code=code, defaults=defaults)
            created += 1 if is_created else 0
            updated += 0 if is_created else 1

        self.message_user(
            request,
            _(f"Sync completed. Created: {created}, Updated: {updated}"),
            level='info'
        )

    sync_policies_from_sap.short_description = _('Sync policies from SAP')

    # Remove add/delete to enforce sync-only updates
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Custom admin URL to trigger sync via a button on change list
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('sync/', self.admin_site.admin_view(self.sync_view), name='sap_integration_policy_sync'),
        ]
        return custom + urls

    def sync_view(self, request):
        self.sync_policies_from_sap(request, Policy.objects.all())
        return redirect('admin:sap_integration_policy_changelist')

# Register your models here.

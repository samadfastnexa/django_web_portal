from django.contrib import admin
from django.utils.html import format_html

from .models import LedgerSettings


class LedgerSettingsAdmin(admin.ModelAdmin):
    """
    Singleton admin — there is always exactly one settings row.
    The 'Add' button is hidden; the single record opens directly.
    """

    # ── Display ───────────────────────────────────────────────────────────────
    list_display = ('__str__', 'group_name', 'stamp_preview', 'sap_logo_preview', 'updated_at')
    readonly_fields = ('updated_at', 'stamp_preview', 'sap_logo_preview')

    fieldsets = (
        ('PDF Header', {
            'fields': ('group_name', 'company_name', 'report_title'),
        }),
        ('Images', {
            'fields': ('smart_stamp_image', 'stamp_preview', 'sap_logo_image', 'sap_logo_preview'),
            'description': (
                'Smart Agriculture Stamp: circular stamp at top-right (150×150 px PNG). '
                'SAP Logo: replaces the auto-drawn blue SAP badge (~110×55 px PNG). '
                'Leave SAP Logo empty to use the built-in drawn badge.'
            ),
        }),
        ('Table Colors', {
            'description': (
                'Customize the PDF table color scheme. Use 6-digit hex codes (e.g. #1e293b). '
                'Changes take effect immediately on the next PDF export.'
            ),
            'fields': (
                'table_header_bg_color', 'table_header_text_color',
                'territory_row_bg_color', 'closing_balance_bg_color',
                'grand_total_bg_color', 'grid_color',
            ),
        }),
        ('Font Sizes', {
            'description': 'Font sizes in points (pt). Typical values: header 11–14, table data 7–9.',
            'fields': (
                'font_size_group_name', 'font_size_company_name',
                'font_size_report_title', 'font_size_dates',
                'font_size_table_header', 'font_size_table_data',
            ),
        }),
        ('Urdu Footer Text', {
            'description': (
                'Printed as paragraphs in the Urdu footer at the bottom of the PDF. '
                'Each new line becomes a separate paragraph.'
            ),
            'fields': ('footer_text',),
        }),
        ('Meta', {
            'fields': ('updated_at',),
            'classes': ('collapse',),
        }),
    )

    # ── Singleton helpers ─────────────────────────────────────────────────────
    def has_add_permission(self, request):
        return not LedgerSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Redirect changelist straight to the single object's change page."""
        from django.shortcuts import redirect
        obj = LedgerSettings.get()
        # Build URL relative to the current admin site (works for both standard and custom)
        info = self.model._meta.app_label, self.model._meta.model_name
        change_url = f'{request.resolver_match.namespace}:{info[0]}_{info[1]}_change'
        try:
            from django.urls import reverse
            return redirect(reverse(change_url, args=[obj.pk]))
        except Exception:
            # fallback: direct path
            base = request.path.rstrip('/')
            return redirect(f'{base}/{obj.pk}/change/')

    # ── Helpers ───────────────────────────────────────────────────────────────
    def stamp_preview(self, obj):
        if obj and obj.smart_stamp_image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;object-fit:contain;'
                'border:1px solid #ccc;border-radius:4px;" />',
                obj.smart_stamp_image.url,
            )
        return '—'
    stamp_preview.short_description = 'Stamp Preview'

    def sap_logo_preview(self, obj):
        if obj and obj.sap_logo_image:
            return format_html(
                '<img src="{}" style="height:40px;object-fit:contain;'
                'border:1px solid #ccc;border-radius:4px;padding:4px;background:#fff;" />',
                obj.sap_logo_image.url,
            )
        return format_html(
            '<span style="display:inline-block;background:#0070f3;color:#fff;'
            'font-weight:bold;font-size:14px;padding:4px 10px;border-radius:3px;">SAP</span> '
            '<em style="color:#888;font-size:11px;">(auto-drawn — upload image to replace)</em>'
        )
    sap_logo_preview.short_description = 'SAP Logo Preview'


# ── Register with standard Django admin ──────────────────────────────────────
admin.site.register(LedgerSettings, LedgerSettingsAdmin)

# ── Register with the custom project admin site ───────────────────────────────
try:
    from web_portal.admin import admin_site as _custom_admin_site
    if not _custom_admin_site.is_registered(LedgerSettings):
        _custom_admin_site.register(LedgerSettings, LedgerSettingsAdmin)
except Exception:
    pass

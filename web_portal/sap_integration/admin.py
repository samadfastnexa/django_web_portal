from django.contrib import admin
from web_portal.admin import admin_site
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import redirect
from django.http import HttpResponse, FileResponse
from .models import Policy, HanaConnect, DiseaseIdentification, RecommendedProduct
from .sap_client import SAPClient
import os
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


def _selected_schema(request):
    """Resolve the HANA schema for the company chosen in the breadcrumb DB selector.

    Reuses the same resolver the APIs use, which reads ?database / session
    'selected_db' (set by the global selector) and maps it to a Company schema.
    """
    try:
        from .views import get_hana_schema_from_request
        return get_hana_schema_from_request(request)
    except Exception:
        return None


def _fetch_policies_from_hana(schema):
    """Fetch currently-valid, active policies for a company schema from SAP HANA.

    Mirrors the default filter of GET /api/sap/policies/ (active=Y and not
    expired by U_InvEndDate/U_Ct) so the admin count matches the API.
    Returns a list of dicts: {code, name, policy, valid_from, valid_to, active(bool)}.
    """
    from .views import sanitize_hana_schema
    schema = sanitize_hana_schema(schema)
    if not schema:
        raise RuntimeError('Invalid or missing database/schema name')

    conn = _hana_connect()
    try:
        cur = conn.cursor()
        cur.execute(f'SET SCHEMA "{schema}"')
        cur.close()

        cur = conn.cursor()
        cur.execute('''
            SELECT
                P."PrjCode"  AS "code",
                P."PrjName"  AS "name",
                P."U_pol"    AS "policy",
                P."ValidFrom" AS "valid_from",
                P."ValidTo"   AS "valid_to",
                P."Active"    AS "active"
            FROM OPRJ P
            WHERE P."U_pol" IS NOT NULL AND P."U_pol" <> ''
              AND P."Active" = 'Y'
              AND (
                    (P."U_InvEndDate" IS NOT NULL AND P."U_InvEndDate" >= CURRENT_DATE)
                 OR (P."U_Ct" IS NOT NULL AND P."U_Ct" >= CURRENT_DATE)
              )
            ORDER BY P."PrjCode"
        ''')
        rows = cur.fetchall()
        cur.close()

        policies = []
        for r in rows:
            policies.append({
                'code': r[0],
                'name': r[1] or '',
                'policy': r[2] or '',
                'valid_from': r[3],
                'valid_to': r[4],
                'active': str(r[5]).strip().upper() == 'Y',
            })
        return policies
    finally:
        conn.close()


def _hana_connect():
    """Open a HANA connection using env-configured credentials."""
    import os
    from pathlib import Path
    from django.conf import settings
    from hdbcli import dbapi
    from .hana_connect import _load_env_file as _hana_load_env_file

    for path in (
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(str(settings.BASE_DIR), '.env'),
        os.path.join(str(Path(settings.BASE_DIR).parent), '.env'),
        os.path.join(os.getcwd(), '.env'),
    ):
        try:
            _hana_load_env_file(path)
        except Exception:
            pass

    host = os.environ.get('HANA_HOST', '')
    port = os.environ.get('HANA_PORT', '30015')
    user = os.environ.get('HANA_USER', '')
    password = os.environ.get('HANA_PASSWORD', '')
    if not host or not user or not password:
        raise RuntimeError('Missing HANA connection parameters in environment')
    return dbapi.connect(address=host, port=int(port), user=user, password=password)


@admin.register(Policy, site=admin_site)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'policy', 'active', 'valid_from', 'valid_to', 'updated_at')
    list_filter = ('active',)
    search_fields = ('database', 'code', 'name', 'policy')
    ordering = ('-updated_at',)  # newest updated first (matches API sort=updated_date&order=desc)
    change_list_template = 'admin/sap_integration/policy/change_list.html'
    readonly_fields = ('database', 'code', 'name', 'policy', 'valid_from', 'valid_to', 'active', 'created_at', 'updated_at')
    actions = ['download_policy_document']

    @admin.action(description=_('Download policy document'))
    def download_policy_document(self, request, queryset):
        """Download the policy document(s) from media for the selection.

        The document file shares the policy name (OPRJ.PrjName, stored in
        Policy.name) and lives in media/product_images/<company>/policies/.
        One selection returns the file directly; multiple selections return a ZIP.
        """
        from .views import locate_policy_file

        found = []
        missing = []

        for p in queryset:
            fpath = locate_policy_file(p.database, p.name)
            if not fpath:
                missing.append(_("%(code)s (%(name)s — no document in media)") % {'code': p.code, 'name': p.name or ''})
                continue
            found.append(fpath)

        if not found:
            self.message_user(
                request,
                _('No policy document found. %(detail)s') % {'detail': '; '.join(str(m) for m in missing)},
                level='error',
            )
            return

        if len(found) == 1:
            fpath = found[0]
            resp = FileResponse(open(fpath, 'rb'), as_attachment=True, filename=os.path.basename(fpath))
            if missing:
                self.message_user(request, _('Some not found: %(d)s') % {'d': '; '.join(str(m) for m in missing)}, level='warning')
            return resp

        # Multiple files -> zip them up.
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fpath in found:
                zf.write(fpath, arcname=os.path.basename(fpath))
        buf.seek(0)
        resp = HttpResponse(buf.getvalue(), content_type='application/zip')
        resp['Content-Disposition'] = 'attachment; filename="policy_documents.zip"'
        if missing:
            self.message_user(request, _('Some not found: %(d)s') % {'d': '; '.join(str(m) for m in missing)}, level='warning')
        return resp

    def _sync_company(self, request, schema):
        """Sync one company's policies from SAP HANA and remove stale local rows."""
        try:
            data = _fetch_policies_from_hana(schema)
        except Exception as e:
            self.message_user(request, _("SAP error for %(db)s: %(err)s") % {'db': schema, 'err': e}, level='error')
            return

        created = 0
        updated = 0
        seen_codes = []

        for row in data:
            code = row.get('code')
            if not code:
                continue
            seen_codes.append(code)
            defaults = {
                'name': row.get('name') or '',
                'policy': row.get('policy') or '',
                'valid_from': _parse_date(row.get('valid_from')),
                'valid_to': _parse_date(row.get('valid_to')),
                'active': bool(row.get('active')),
            }
            obj, is_created = Policy.objects.update_or_create(
                database=schema, code=code, defaults=defaults
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1

        # Remove policies for this company that no longer exist in SAP.
        removed, _details = Policy.objects.filter(database=schema).exclude(code__in=seen_codes).delete()

        self.message_user(
            request,
            _("Sync completed for %(db)s. Created: %(c)d, Updated: %(u)d, Removed: %(r)d") % {
                'db': schema, 'c': created, 'u': updated, 'r': removed,
            },
            level='info',
        )

    # Remove add/delete to enforce sync-only updates
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """Show only the company selected in the breadcrumb DB selector."""
        qs = super().get_queryset(request)
        schema = _selected_schema(request)
        if schema:
            qs = qs.filter(database=schema)
        return qs

    # Custom admin URL to trigger sync via a button on change list
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('sync/', self.admin_site.admin_view(self.sync_view), name='sap_integration_policy_sync'),
        ]
        return custom + urls

    def sync_view(self, request):
        # Sync the company currently selected in the breadcrumb DB selector.
        schema = _selected_schema(request)
        if not schema:
            self.message_user(
                request,
                _('No company selected. Pick a company from the DB selector in the top bar first.'),
                level='warning',
            )
            return redirect('admin:sap_integration_policy_changelist')
        self._sync_company(request, schema)
        return redirect('admin:sap_integration_policy_changelist')

@admin.register(HanaConnect, site=admin_site)
class HanaConnectAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        # Check permission: only staff members with specific permission can access
        if not request.user.is_staff or not request.user.has_perm('sap_integration.access_hana_connect'):
            from django.contrib.admin import site
            return site.index(request)
        return redirect('hana_connect_admin')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class RecommendedProductInline(admin.TabularInline):
    """Inline admin for recommended products"""
    model = RecommendedProduct
    extra = 1
    fields = ('product_item_code', 'product_name', 'dosage', 'priority', 'effectiveness_rating', 'is_active')
    ordering = ('priority', '-effectiveness_rating')


@admin.register(DiseaseIdentification, site=admin_site)
class DiseaseIdentificationAdmin(admin.ModelAdmin):
    """Admin for Disease Identification"""
    list_display = ('item_code', 'disease_name', 'item_name', 'is_active', 'recommended_count', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('item_code', 'disease_name', 'item_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RecommendedProductInline]
    actions = ['sync_diseases_from_sap']
    change_list_template = 'admin/sap_integration/diseaseidentification/change_list.html'
    
    fieldsets = (
        (_('SAP Information'), {
            'fields': ('doc_entry', 'item_code', 'item_name')
        }),
        (_('Disease Details'), {
            'fields': ('disease_name', 'description', 'is_active')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def recommended_count(self, obj):
        """Count of active recommended products"""
        count = obj.recommended_products.filter(is_active=True).count()
        return f"{count} product(s)"
    recommended_count.short_description = 'Recommended Products'
    
    def sync_diseases_from_sap(self, request, queryset):
        """Admin action: Sync diseases from SAP @ODID table"""
        selected_db = request.session.get('selected_db', '4B-BIO')
        client = SAPClient(company_db_key=selected_db)
        
        try:
            diseases = client.get_diseases()
        except Exception as e:
            self.message_user(request, _(f"SAP error: {e}"), level='error')
            return
        
        created = 0
        updated = 0
        
        for disease_data in diseases:
            item_code = disease_data.get('item_code', '').strip()
            if not item_code:
                continue
            
            defaults = {
                'doc_entry': disease_data.get('doc_entry', ''),
                'item_name': disease_data.get('item_name', ''),
                'description': disease_data.get('description', ''),
                'disease_name': disease_data.get('disease_name', ''),
                'is_active': True,
            }
            
            obj, is_created = DiseaseIdentification.objects.update_or_create(
                item_code=item_code,
                defaults=defaults
            )
            created += 1 if is_created else 0
            updated += 0 if is_created else 1
        
        self.message_user(
            request,
            _(f"Sync completed. Created: {created}, Updated: {updated}"),
            level='info'
        )
    
    sync_diseases_from_sap.short_description = _('Sync diseases from SAP @ODID table')
    
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('sync-sap/', self.admin_site.admin_view(self.sync_view), name='disease_sync_sap'),
        ]
        return custom + urls
    
    def sync_view(self, request):
        """Custom view to trigger sync via button on change list"""
        self.sync_diseases_from_sap(request, None)
        from django.shortcuts import redirect
        return redirect('..')
    
    def get_queryset(self, request):
        """Optimize query to include related products"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('recommended_products')


@admin.register(RecommendedProduct, site=admin_site)
class RecommendedProductAdmin(admin.ModelAdmin):
    """Admin for Recommended Products"""
    list_display = (
        'product_name', 'product_item_code', 'disease_link', 'priority',
        'effectiveness_rating', 'is_active', 'updated_at'
    )
    list_filter = ('is_active', 'priority', 'disease', 'effectiveness_rating')
    search_fields = (
        'product_item_code', 'product_name', 'disease__disease_name',
        'disease__item_code', 'dosage', 'application_method'
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['disease']
    
    fieldsets = (
        (_('Product Information'), {
            'fields': ('disease', 'product_item_code', 'product_name')
        }),
        (_('Recommendation Details'), {
            'fields': ('dosage', 'application_method', 'timing', 'precautions')
        }),
        (_('Priority & Effectiveness'), {
            'fields': ('priority', 'effectiveness_rating', 'is_active')
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def disease_link(self, obj):
        """Display disease name as link"""
        from django.utils.html import format_html
        from django.urls import reverse
        url = reverse('admin:sap_integration_diseaseidentification_change', args=[obj.disease.pk])
        return format_html('<a href="{}">{}</a>', url, obj.disease.disease_name)
    disease_link.short_description = 'Disease'
    disease_link.admin_order_field = 'disease__disease_name'
    
    def get_queryset(self, request):
        """Optimize query to include related disease"""
        qs = super().get_queryset(request)
        return qs.select_related('disease')

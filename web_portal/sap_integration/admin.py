from django.contrib import admin
from web_portal.admin import admin_site
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import redirect
from .models import Policy, HanaConnect, DiseaseIdentification, RecommendedProduct
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


@admin.register(Policy, site=admin_site)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'policy', 'active', 'valid_from', 'valid_to', 'updated_at')
    list_filter = ('active',)
    search_fields = ('code', 'name', 'policy')
    actions = ['sync_policies_from_sap']
    change_list_template = 'admin/sap_integration/policy/change_list.html'
    readonly_fields = ('code', 'name', 'policy', 'valid_from', 'valid_to', 'active', 'created_at', 'updated_at')

    def sync_policies_from_sap(self, request, queryset):
        """Admin action: Sync policies from SAP Projects (UDF U_pol)."""
        selected_db = request.session.get('selected_db', '4B-BIO')
        client = SAPClient(company_db_key=selected_db)
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

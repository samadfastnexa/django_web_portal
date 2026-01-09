from django.contrib import admin
from sap_integration.views import (
    hana_connect_admin,
    bp_entry_admin,
    bp_lookup_admin,
    sales_order_admin,
    sales_vs_achievement_api,
    sales_vs_achievement_by_emp_api,
    territory_summary_api,
    products_catalog_api,
    hana_health_api,
    hana_count_tables_api,
    select_oitm_api,
    set_database,
)
from general_ledger.views import (
    general_ledger_admin,
    export_ledger_csv,
    export_ledger_pdf,
)
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.shortcuts import redirect 

from django.conf import settings
from django.conf.urls.static import static

# Import custom admin site
from django.utils.module_loading import autodiscover_modules
from web_portal.admin import admin_site

# Ensure all admin modules load into the custom admin site registry
autodiscover_modules("admin", register_to=admin_site)

# Admin Site Configuration - Use custom admin site for analytics
admin_site.site_header = getattr(settings, 'ADMIN_SITE_HEADER', 'Django Administration')
admin_site.site_title = getattr(settings, 'ADMIN_SITE_TITLE', 'Django Admin')
admin_site.index_title = getattr(settings, 'ADMIN_INDEX_TITLE', 'Site Administration')

schema_view = get_schema_view(
   openapi.Info(
      title="web portal API",
      default_version='v1',
      description="web portal API for user management",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    path('', lambda request: redirect('/admin/', permanent=False)), # Redirect root(http://127.0.0.1:8000) URL to admin
    path('admin/set-database/', admin_site.admin_view(set_database), name='set_database'),
    path('admin/general-ledger/', admin_site.admin_view(general_ledger_admin), name='general_ledger_admin'),
    path('admin/general-ledger/export-csv/', admin_site.admin_view(export_ledger_csv), name='export_ledger_csv'),
    path('admin/general-ledger/export-pdf/', admin_site.admin_view(export_ledger_pdf), name='export_ledger_pdf'),
    path('admin/hana-connect/', admin_site.admin_view(hana_connect_admin), name='hana_connect_admin'),
    path('admin/sap-bp-entry/', admin_site.admin_view(bp_entry_admin), name='sap_bp_entry_admin'),
    path('admin/sap-bp-lookup/', admin_site.admin_view(bp_lookup_admin), name='sap_bp_lookup_admin'),
    path('admin/sap-sales-order/', admin_site.admin_view(sales_order_admin), name='sap_sales_order_admin'),
    path('api/sap/sales-vs-achievement/', sales_vs_achievement_api, name='sales_vs_achievement_api'),
    path('api/sap/sales-vs-achievement-by-emp/', sales_vs_achievement_by_emp_api, name='sales_vs_achievement_by_emp_api'),
    path('api/sap/territory-summary/', territory_summary_api, name='territory_summary_api'),
    path('api/sap/products-catalog/', products_catalog_api, name='products_catalog_api'),
    # Moved to sap_integration/urls.py: path('api/sap/policy-customer-balance/', ...)
    path('api/sap/health/', hana_health_api, name='hana_health_api'),
    path('api/sap/count-tables/', hana_count_tables_api, name='hana_count_tables_api'),
    path('api/sap/select-oitm/', select_oitm_api, name='select_oitm_api'),
    path('admin/', admin_site.urls),  # Use custom admin site
    
    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # App APIs
    path('api/', include('accounts.urls')),  # ✅ all accounts related routes
    path('api/complaints/',include('complaints.urls')),
    path('api/farmers/',include('farmers.urls')),
    path('api/',include('preferences.urls')),
    path('api/',include('attendance.urls')),
    path('api/',include('farmerMeetingDataEntry.urls')),
    path('api/field/',include('FieldAdvisoryService.urls')), 
    path('api/farm/',include('farm.urls')),
    path('api/sap/', include('sap_integration.urls')),
    path('api/crop-management/', include('crop_management.urls')),
     path('api/', include('crop_manage.urls')),  # <-- add this
    path('api/kindwise/', include('kindwise.urls')),  # Kindwise app URLs
    path('api/analytics/', include('analytics.urls')),  # Analytics dashboard APIs
    path('', include('general_ledger.urls')),  # General Ledger app URLs (includes both API and admin routes)
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

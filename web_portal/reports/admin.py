from django.contrib import admin

from .models import BranchAccess, Report, SalesEmployeeAccess, UserReportAccess

# This project serves a custom AnalyticsAdminSite, not django.contrib.admin.site,
# so registering on the default site would leave these models out of /admin/
# entirely. Registering on admin_site also picks up the site-wide export actions
# and detailed form-error summaries. The fallback keeps the app a drop-in for a
# plain Django project that has no custom site.
try:
    from web_portal.admin import admin_site
except ImportError:  # pragma: no cover - standalone install
    admin_site = admin.site


@admin.register(Report, site=admin_site)
class ReportAdmin(admin.ModelAdmin):
    # Adds a "Generate Report" button to the changelist toolbar so the run page
    # is reachable from the admin rather than only by typing the URL.
    change_list_template = "admin/reports/report_changelist.html"
    list_display = ("name", "display_name", "default_format", "is_active")
    list_filter = ("is_active", "default_format")
    search_fields = ("name", "display_name")
    list_per_page = 25


@admin.register(UserReportAccess, site=admin_site)
class UserReportAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "report", "granted_at")
    list_filter = ("report",)
    search_fields = ("user__email", "user__username", "report__name")
    autocomplete_fields = ("report",)
    list_per_page = 25


@admin.register(BranchAccess, site=admin_site)
class BranchAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "branch_id")
    search_fields = ("user__email", "user__username", "branch_id")
    list_per_page = 25


@admin.register(SalesEmployeeAccess, site=admin_site)
class SalesEmployeeAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "sales_employee_id")
    search_fields = ("user__email", "user__username", "sales_employee_id")
    list_per_page = 25

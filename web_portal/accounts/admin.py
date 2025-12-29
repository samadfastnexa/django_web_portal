from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, SalesStaffProfile
from web_portal.admin import admin_site

# Inline for Sales Staff profile
class SalesProfileInline(admin.StackedInline):
    model = SalesStaffProfile
    can_delete = False
    verbose_name_plural = 'Sales Profile'
    fieldsets = (
        ('Basic Info', {
            'fields': ('employee_code', 'phone_number', 'designation', 'address')
        }),
        ('Location', {
            'fields': ('companies', 'regions', 'zones', 'territories')  # ✅ updated M2M
        }),
        ('Reporting', {
            'fields': ('hod', 'master_hod')
        }),
        ('Leave Quotas', {
            'fields': ('sick_leave_quota', 'casual_leave_quota', 'others_leave_quota')
        }),
    )
    filter_horizontal = ('companies', 'regions', 'zones', 'territories')  # ✅ better M2M UI


@admin.register(User, site=admin_site)
class CustomUserAdmin(BaseUserAdmin):
    list_display = [
        'id', 'username', 'email', 'first_name', 'last_name',
        'role', 'is_active', 'is_sales_staff'
    ]
    list_filter = ['role', 'is_active', 'is_staff', 'is_sales_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['id']

    # ✅ Allow quick edits for role & is_active
    list_editable = ['role', 'is_active']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'profile_image', 'is_sales_staff')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'role', 'profile_image', 'is_sales_staff')}),
    )

    inlines = [SalesProfileInline]  # Attach inline here


@admin.register(Role, site=admin_site)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    filter_horizontal = ['permissions']
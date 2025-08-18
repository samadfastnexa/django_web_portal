from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, SalesStaffProfile

# Inline for Sales Staff profile
class SalesProfileInline(admin.StackedInline):
    model = SalesStaffProfile
    can_delete = False
    verbose_name_plural = 'Sales Profile'

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ['id', 'username', 'email', 'first_name', 'last_name', 'role']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'email']
    ordering = ['id']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'profile_image')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'profile_image')}),
    )

    inlines = [SalesProfileInline]  # ✅ Attach inline here

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    filter_horizontal = ['permissions']

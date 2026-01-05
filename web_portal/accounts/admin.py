from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from django.db.models import Q
from .models import User, Role, SalesStaffProfile
from web_portal.admin import admin_site

# Inline for Sales Staff profile
class SalesProfileInline(admin.StackedInline):
    model = SalesStaffProfile
    can_delete = False
    verbose_name_plural = 'Sales Profile'
    extra = 0  # ✅ Don't create empty inline forms by default
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
    
    def has_add_permission(self, request, obj=None):
        """Prevent adding profiles directly from User edit (go to SalesStaffProfile admin instead)"""
        return False


@admin.register(User, site=admin_site)
class CustomUserAdmin(BaseUserAdmin):
    list_display = [
        'id', 'username', 'email', 'role', 'is_active', 'is_sales_staff'
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

    inlines = [SalesProfileInline]  # Attach inline here (read-only display only)
    
    class Media:
        css = {
            'all': ('css/admin_user_custom.css',)
        }
    
    def changelist_view(self, request, extra_context=None):
        """Override changelist view to handle database integrity errors gracefully"""
        try:
            return super().changelist_view(request, extra_context)
        except Exception as e:
            # Catch any database errors and display as warning
            error_msg = str(e)
            if 'user_id' in error_msg and 'null' in error_msg:
                self.message_user(
                    request,
                    '⚠️ Warning: Cannot save - SalesStaffProfile requires a valid user assignment. Please check the SalesStaffProfile admin.',
                    messages.WARNING
                )
            else:
                self.message_user(
                    request,
                    f'⚠️ Warning: Database error - {error_msg[:80]}',
                    messages.WARNING
                )
            # Re-raise to show error on page, but message is now displayed
            raise
    
    def delete_model(self, request, obj):
        """Prevent deletion if user has SalesStaffProfile"""
        try:
            if hasattr(obj, 'sales_profile') and obj.sales_profile:
                self.message_user(
                    request,
                    f'❌ Cannot delete user "{obj.email}" - User has an active SalesStaffProfile. Delete the profile first from SalesStaffProfile admin.',
                    messages.ERROR
                )
                return  # Don't delete
        except Exception:
            pass
        
        # Safe to delete
        super().delete_model(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """Check if user has a sales profile before allowing deletion"""
        if obj and hasattr(obj, 'sales_profile'):
            try:
                if obj.sales_profile:
                    return False  # Don't allow deletion
            except Exception:
                pass
        return True


@admin.register(Role, site=admin_site)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    filter_horizontal = ['permissions']


@admin.register(SalesStaffProfile, site=admin_site)
class SalesStaffProfileAdmin(admin.ModelAdmin):
    """Admin for SalesStaffProfile with data integrity checks"""
    list_display = ['id', 'designation', 'employee_code', 'user_display', 'is_vacant']
    list_filter = ['designation', 'is_vacant', 'employee_code']
    search_fields = ['user__email', 'user__username', 'employee_code']
    filter_horizontal = ('companies', 'regions', 'zones', 'territories')
    
    fieldsets = (
        ('User Assignment', {
            'fields': ('user', 'is_vacant')
        }),
        ('Basic Info', {
            'fields': ('employee_code', 'phone_number', 'designation', 'address')
        }),
        ('Location', {
            'fields': ('companies', 'regions', 'zones', 'territories')
        }),
        ('Reporting', {
            'fields': ('hod', 'master_hod')
        }),
        ('Leave Quotas', {
            'fields': ('sick_leave_quota', 'casual_leave_quota', 'others_leave_quota')
        }),
    )
    
    def user_display(self, obj):
        """Display user safely"""
        if obj.user:
            return f"{obj.user.email}"
        elif obj.is_vacant:
            return "🔴 VACANT"
        return "⚠️ UNASSIGNED"
    user_display.short_description = 'User'
    
    def changelist_view(self, request, extra_context=None):
        """Check for data integrity issues"""
        try:
            # Find profiles with null user that are not marked as vacant
            orphaned = SalesStaffProfile.objects.filter(
                Q(user_id__isnull=True) & Q(is_vacant=False)
            )
            if orphaned.exists():
                self.message_user(
                    request,
                    f'ℹ️ Info: {orphaned.count()} profile(s) have no user assigned and are not marked vacant. Consider marking as vacant or assigning a user.',
                    messages.INFO
                )
        except Exception as e:
            self.message_user(
                request,
                f'⚠️ Warning: Could not check data integrity. {str(e)[:80]}',
                messages.WARNING
            )
        
        return super().changelist_view(request, extra_context)
    
    def save_model(self, request, obj, form, change):
        """Validate before saving - user required unless marked vacant"""
        # Validate: user is required unless marked as vacant
        if not obj.user and not obj.is_vacant:
            self.message_user(
                request,
                '❌ Error: SalesStaffProfile must have a user assigned OR be marked as vacant.',
                messages.ERROR
            )
            return  # Prevent save
        
        try:
            super().save_model(request, obj, form, change)
            self.message_user(request, '✅ Profile saved successfully.', messages.SUCCESS)
        except Exception as e:
            error_msg = str(e)
            if 'user_id' in error_msg and 'null' in error_msg:
                self.message_user(
                    request,
                    '❌ Error: User field cannot be null. Please assign a user or mark as vacant.',
                    messages.ERROR
                )
            else:
                self.message_user(
                    request,
                    f'❌ Error saving: {error_msg[:100]}',
                    messages.ERROR
                )
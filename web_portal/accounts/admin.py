from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from django.db.models import Q
from .models import User, Role, SalesStaffProfile
from web_portal.admin import admin_site

# Import Dealer model for the inline
try:
    from FieldAdvisoryService.models import Dealer
    HAS_DEALER = True
except ImportError:
    HAS_DEALER = False

# Inline for Sales Staff profile
class SalesProfileInline(admin.StackedInline):
    model = SalesStaffProfile
    can_delete = False
    verbose_name_plural = 'Sales Profile'
    extra = 1  # ✅ Show one empty form so users can create profile directly from user edit
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
        """Allow adding profiles from User edit if user is marked as sales_staff"""
        return True


# Inline for Dealer profile - imported dynamically to avoid circular imports
if HAS_DEALER:
    class DealerInline(admin.StackedInline):
        model = Dealer
        fk_name = 'user'  # ✅ Specify which ForeignKey to use (user, not created_by)
        verbose_name_plural = 'Dealer Profile'
        can_delete = True  # ✅ Allow deletion
        extra = 1  # ✅ Show one empty form so users can create dealer profile directly from user edit
        fieldsets = (
            ('Basic Info', {
                'fields': ('card_code', 'business_name', 'cnic_number')  # name derived from user
            }),
            ('Contact Information', {
                'fields': ('email', 'contact_number', 'mobile_phone')
            }),
            ('Address', {
                'fields': ('address', 'city', 'state', 'country', 'latitude', 'longitude')
            }),
            ('Location Assignment', {
                'fields': ('company', 'region', 'zone', 'territory')
            }),
            ('Tax & Legal Information', {
                'fields': ('federal_tax_id', 'additional_id', 'unified_federal_tax_id', 'filer_status'),
                'classes': ('collapse',)
            }),
            ('License Information', {
                'fields': ('govt_license_number', 'license_expiry', 'u_leg'),
                'classes': ('collapse',)
            }),
            ('SAP Configuration', {
                'fields': ('sap_series', 'card_type', 'group_code', 'debitor_account', 'vat_group', 'vat_liable', 'whatsapp_messages'),
                'classes': ('collapse',)
            }),
            ('Financial', {
                'fields': ('minimum_investment',),
                'classes': ('collapse',)
            }),
            ('CNIC Images', {
                'fields': ('cnic_front_image', 'cnic_back_image'),
                'classes': ('collapse',)
            }),
            ('Additional Information', {
                'fields': ('remarks',),
                'classes': ('collapse',)
            }),
            ('Status', {
                'fields': ('is_active',)
            }),
        )
        raw_id_fields = ('company', 'region', 'zone', 'territory')
        readonly_fields = ('created_at', 'updated_at', 'created_by')
        
        def has_add_permission(self, request, obj=None):
            """Allow adding dealer profiles from User edit if user is marked as is_dealer"""
            return True


@admin.register(User, site=admin_site)
class CustomUserAdmin(BaseUserAdmin):
    list_display = [
        'id', 'username', 'email', 'role', 'is_active', 'is_sales_staff', 'is_dealer'
    ]
    list_filter = ['role', 'is_active', 'is_staff', 'is_sales_staff', 'is_dealer']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['id']

    # ✅ Allow quick edits for role & is_active & is_dealer
    list_editable = ['role', 'is_active', 'is_dealer']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'profile_image', 'is_sales_staff', 'is_dealer')}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('email', 'role', 'profile_image', 'is_sales_staff', 'is_dealer')}),
    )

    # Add DealerInline only if Dealer model is available
    inlines = [SalesProfileInline]
    if HAS_DEALER:
        inlines.append(DealerInline)
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of protected superuser"""
        if obj and obj.email == 'superuser@gmail.com':
            return False
        return super().has_delete_permission(request, obj)
    
    def delete_model(self, request, obj):
        """Prevent deletion of protected superuser"""
        if obj.email == 'superuser@gmail.com':
            from django.contrib import messages
            messages.error(request, f'Cannot delete protected superuser: {obj.email}')
            return
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Prevent bulk deletion of protected superuser"""
        protected = queryset.filter(email='superuser@gmail.com')
        if protected.exists():
            from django.contrib import messages
            messages.error(request, 'Cannot delete protected superuser: superuser@gmail.com')
            queryset = queryset.exclude(email='superuser@gmail.com')
        super().delete_queryset(request, queryset)
    if HAS_DEALER:
        inlines.append(DealerInline)
    
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
    
    def save_formset(self, request, form, formset, change):
        """Handle dealer inline: set created_by, sync is_dealer, derive name from user"""
        instances = formset.save(commit=False)
        
        for instance in instances:
            # Handle Dealer inline - set created_by and is_dealer flag
            if hasattr(instance, 'created_by') and hasattr(instance, 'user'):
                # Set created_by if not already set
                if not instance.created_by:
                    instance.created_by = request.user
                
                # Ensure is_dealer flag is set on user
                if instance.user and not instance.user.is_dealer:
                    instance.user.is_dealer = True
                    instance.user.save(update_fields=["is_dealer"])

                # Derive dealer.name from linked user's name
                if instance.user:
                    first = getattr(instance.user, 'first_name', '') or ''
                    last = getattr(instance.user, 'last_name', '') or ''
                    full = (first + ' ' + last).strip()
                    if not full:
                        full = getattr(instance.user, 'username', None) or getattr(instance.user, 'email', '')
                    instance.name = full
            
            instance.save()
        
        formset.save_m2m()


@admin.register(Role, site=admin_site)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    filter_horizontal = ['permissions']
    
    # Protected roles that cannot be deleted
    PROTECTED_ROLES = ['Admin', 'Dealer', 'Sales Staff', 'Farmer']
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of protected roles"""
        if obj and obj.name in self.PROTECTED_ROLES:
            return False
        return super().has_delete_permission(request, obj)
    
    def delete_model(self, request, obj):
        """Prevent deletion of protected roles"""
        if obj.name in self.PROTECTED_ROLES:
            from django.contrib import messages
            messages.error(request, f'Cannot delete protected role: {obj.name}')
            return
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Prevent bulk deletion of protected roles"""
        protected = queryset.filter(name__in=self.PROTECTED_ROLES)
        if protected.exists():
            from django.contrib import messages
            protected_names = ', '.join(protected.values_list('name', flat=True))
            messages.error(request, f'Cannot delete protected roles: {protected_names}')
            queryset = queryset.exclude(name__in=self.PROTECTED_ROLES)
        super().delete_queryset(request, queryset)


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



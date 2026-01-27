from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import messages
from django.db.models import Q
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from .models import User, Role, SalesStaffProfile, DesignationModel
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
    can_delete = True
    verbose_name_plural = 'Sales Profile'
    extra = 0  # Don't show empty forms by default
    max_num = 1  # Only one sales profile per user
    show_change_link = True  # Add link to edit profile separately
    
    # Make fields not required for deletion
    def get_formset(self, request, obj=None, **kwargs):
        """Customize the formset to allow deletion even with required fields empty"""
        formset = super().get_formset(request, obj, **kwargs)
        
        # Make fields optional in the form to allow deletion
        for field_name in ['phone_number', 'address', 'designation']:
            if field_name in formset.form.base_fields:
                formset.form.base_fields[field_name].required = False
        
        return formset
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('employee_code', 'phone_number', 'designation', 'address'),
            'description': '📱 Phone number can be used for login instead of email'
        }),
        ('Location', {
            'fields': ('companies', 'regions', 'zones', 'territories')  # ✅ updated M2M
        }),
        ('Reporting Hierarchy', {
            'fields': ('manager', 'hod', 'master_hod'),
            'description': 'Reporting hierarchy: manager = direct supervisor in reporting chain'
        }),
        ('Leave Quotas', {
            'fields': ('sick_leave_quota', 'casual_leave_quota', 'others_leave_quota')
        }),
    )
    filter_horizontal = ('companies', 'regions', 'zones', 'territories')  # ✅ better M2M UI
    
    def has_add_permission(self, request, obj=None):
        """Allow adding profiles from User edit if user is marked as sales_staff"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of sales profiles"""
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
    
    def save_formset(self, request, form, formset, change):
        """
        Override save_formset to properly handle deletion of sales profiles.
        This ensures that when the delete checkbox is checked, the profile is actually deleted.
        """
        instances = formset.save(commit=False)
        
        # Handle deletions explicitly
        for obj in formset.deleted_objects:
            obj.delete()
        
        # Save new/modified instances
        for instance in instances:
            instance.save()
        
        # Save many-to-many relationships
        formset.save_m2m()
    
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
    list_display = ['id', 'designation', 'employee_code', 'phone_number', 'user_display', 'manager_display', 'subordinates_count', 'is_vacant']
    list_filter = ['designation', 'is_vacant', 'employee_code']
    search_fields = ['user__email', 'user__username', 'employee_code', 'phone_number']
    filter_horizontal = ('companies', 'regions', 'zones', 'territories')
    raw_id_fields = ('manager', 'hod', 'master_hod')
    
    fieldsets = (
        ('User Assignment', {
            'fields': ('user', 'is_vacant')
        }),
        ('Basic Info', {
            'fields': ('employee_code', 'phone_number', 'designation', 'address'),
            'description': '📱 Phone number can be used for login instead of email'
        }),
        ('Location', {
            'fields': ('companies', 'regions', 'zones', 'territories')
        }),
        ('Reporting Hierarchy', {
            'fields': ('manager', 'hod', 'master_hod'),
            'description': 'Manager = direct supervisor in reporting chain. Subordinates will see this person\'s data.'
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
    
    def manager_display(self, obj):
        """Display manager in list view"""
        if obj.manager:
            return f"{obj.manager}"
        return "—"
    manager_display.short_description = 'Reports To'
    
    def subordinates_count(self, obj):
        """Display count of subordinates"""
        try:
            count = obj.subordinates.filter(is_vacant=False).count()
            if count > 0:
                return f"👥 {count}"
            return "—"
        except:
            return "—"
    subordinates_count.short_description = 'Team Size'
    
    def save_model(self, request, obj, form, change):
        """Override save to handle validation properly"""
        # Save the object first (without M2M validation)
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        """Validate M2M fields after they're saved"""
        # Save M2M fields first
        super().save_related(request, form, formsets, change)
        
        # Now validate with M2M data available
        obj = form.instance
        if obj.user and getattr(obj.user, 'is_sales_staff', False):
            designation_code = obj.designation.code if obj.designation else None
            
            # Skip validation for CEO/NSM
            if designation_code in ['CEO', 'NSM']:
                return
            
            # Regional Sales Leader → at least 1 region
            if designation_code == 'RSL':
                if not obj.regions.exists():
                    messages.error(request, f"❌ Regional Sales Leader must have at least one region assigned.")
                    return
            
            # Zonal level → at least 1 zone
            elif designation_code in ['DRSL', 'ZM']:
                if not obj.zones.exists():
                    messages.error(request, f"❌ Zonal-level staff must have at least one zone assigned.")
                    return
            
            # Territory level → at least 1 territory
            elif designation_code in ['PL', 'SR_PL', 'FSM', 'SR_FSM', 'DPL', 'MTO', 'SR_MTO']:
                if not obj.territories.exists():
                    messages.error(request, f"❌ Territory-level staff must have at least one territory assigned.")
                    return
        
        messages.success(request, f"✅ Sales staff profile saved successfully.")
    
    actions = ['view_hierarchy_tree', 'view_reporting_chain']
    
    def view_hierarchy_tree(self, request, queryset):
        """Show hierarchy tree for selected profiles"""
        if queryset.count() != 1:
            self.message_user(
                request,
                '⚠️ Please select exactly one profile to view hierarchy tree.',
                messages.WARNING
            )
            return
        
        profile = queryset.first()
        subordinates = profile.get_all_subordinates(include_self=False)
        chain = profile.get_reporting_chain(include_self=True)
        
        # Build hierarchy message
        msg_lines = [f"\n📊 Hierarchy for {profile}:\n"]
        
        # Show reporting chain (upward)
        msg_lines.append("📈 Reports to:")
        for i, manager in enumerate(chain[1:], 1):  # Skip self
            indent = "  " * i
            msg_lines.append(f"{indent}↑ {manager} ({manager.designation})")
        if len(chain) == 1:
            msg_lines.append("  → Top level (no manager)")
        
        # Show subordinates (downward)
        msg_lines.append(f"\n👥 Team ({subordinates.count()} subordinates):")
        if subordinates.exists():
            for sub in subordinates:
                is_direct = "Direct" if sub.manager_id == profile.id else "Indirect"
                msg_lines.append(f"  • {sub} ({sub.designation}) - {is_direct}")
        else:
            msg_lines.append("  → No subordinates")
        
        self.message_user(request, "\n".join(msg_lines), messages.INFO)
    
    view_hierarchy_tree.short_description = "📊 View hierarchy tree"
    
    def view_reporting_chain(self, request, queryset):
        """Show reporting chain to CEO"""
        selected = queryset.count()
        msg_lines = []
        
        for profile in queryset[:5]:  # Limit to 5 to avoid spam
            chain = profile.get_reporting_chain(include_self=True)
            chain_str = " → ".join([f"{p} ({p.designation})" for p in chain])
            msg_lines.append(f"• {chain_str}")
        
        if selected > 5:
            msg_lines.append(f"... and {selected - 5} more")
        
        self.message_user(
            request,
            "📈 Reporting Chains:\n" + "\n".join(msg_lines),
            messages.INFO
        )
    
    view_reporting_chain.short_description = "📈 View reporting chain"
    
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


@admin.register(DesignationModel, site=admin_site)
class DesignationAdmin(admin.ModelAdmin):
    """Admin for dynamic Designation management"""
    list_display = ['code', 'name', 'level', 'is_active', 'staff_count']
    list_filter = ['is_active', 'level']
    search_fields = ['code', 'name', 'description']
    ordering = ['level', 'name']
    list_editable = ['level', 'is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'level')
        }),
        ('Details', {
            'fields': ('description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def staff_count(self, obj):
        """Show count of staff with this designation"""
        count = obj.staff_members.filter(is_vacant=False).count()
        if count > 0:
            return f"👥 {count}"
        return "—"
    staff_count.short_description = 'Active Staff'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion if designation is in use"""
        if obj and obj.staff_members.exists():
            return False
        return super().has_delete_permission(request, obj)
    
    def delete_model(self, request, obj):
        """Check if designation is in use before deletion"""
        if obj.staff_members.exists():
            self.message_user(
                request,
                f'❌ Cannot delete "{obj.name}" - {obj.staff_members.count()} staff member(s) are using this designation.',
                messages.ERROR
            )
            return
        super().delete_model(request, obj)


# ==================== ORGANOGRAM ADMIN VIEW ====================
class OrganogramAdminView:
    """
    Custom admin view for displaying organization hierarchy.
    Accessible via Admin panel with proper permissions.
    """
    
    @staticmethod
    @staff_member_required
    def organogram_view(request):
        """Render the organogram page"""
        
        # Check permission
        if not request.user.is_superuser and not request.user.has_perm('accounts.view_organogram'):
            messages.error(request, "You don't have permission to view the organogram.")
            return render(request, 'admin/permission_denied.html')
        
        # Get hierarchy data
        hierarchy_data = OrganogramAdminView._build_hierarchy()
        
        context = {
            'title': 'Organization Hierarchy (Organogram)',
            'hierarchy_data': hierarchy_data,
            'has_permission': True,
            'site_header': admin_site.site_header,
            'site_title': admin_site.site_title,
        }
        
        return render(request, 'admin/organogram.html', context)
    
    @staticmethod
    def _build_hierarchy():
        """Build hierarchical structure for admin display"""
        from django.core.serializers.json import DjangoJSONEncoder
        import json
        
        # Get all sales profiles (including vacant ones)
        profiles = SalesStaffProfile.objects.select_related(
            'user', 'designation', 'manager'
        ).prefetch_related(
            'companies', 'regions', 'zones', 'territories'
        )
        
        # Find top-level managers (those without a manager)
        top_level = profiles.filter(manager__isnull=True)
        
        def build_node(profile):
            """Recursively build node"""
            # Handle vacant positions
            if profile.is_vacant or not profile.user:
                name = f"Vacant ({profile.designation.name if profile.designation else 'Position'})"
                email = ""
            else:
                name = f"{profile.user.first_name} {profile.user.last_name}"
                email = profile.user.email
            
            node = {
                'id': profile.id,
                'name': name,
                'designation': profile.designation.name if profile.designation else "N/A",
                'designation_code': profile.designation.code if profile.designation else "",
                'employee_code': profile.employee_code or "N/A",
                'email': email,
                'phone': profile.phone_number or "",
                'companies': list(profile.companies.values_list('Company_name', flat=True)),
                'regions': list(profile.regions.values_list('name', flat=True)),
                'zones': list(profile.zones.values_list('name', flat=True)),
                'territories': list(profile.territories.values_list('name', flat=True)),
                'is_vacant': profile.is_vacant,
            }
            
            # Get subordinates (including vacant ones)
            subordinates = profile.subordinates.all().order_by('designation__level', 'user__first_name')
            if subordinates.exists():
                node['children'] = [build_node(sub) for sub in subordinates]
            
            return node
        
        hierarchy = [build_node(profile) for profile in top_level]
        return json.dumps(hierarchy, cls=DjangoJSONEncoder)


# Register custom admin view URL
class CustomAdminSite(admin.AdminSite):
    """Custom admin site with organogram view"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('organogram/', OrganogramAdminView.organogram_view, name='organogram'),
        ]
        return custom_urls + urls


# Add organogram link to admin index (optional)
# This will be accessible via /admin/organogram/

from django.contrib import admin
from web_portal.admin import admin_site
from django.utils.html import format_html
from .models import Farm


@admin.register(Farm, site=admin_site)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "size", "soil_type", "is_active", "status_display", "created_at")
    list_filter = ("soil_type", "is_active", "created_at", "deleted_at")
    search_fields = ("name", "owner__username", "soil_type")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "owner", "address", "geolocation")
        }),
        ("Farm Details", {
            "fields": ("size", "soil_type", "ownership_details")
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "deleted_at"),
            "classes": ("collapse",)
        }),
    )
    
    def status_display(self, obj):
        """Display farm status with color coding"""
        if obj.is_deleted:
            return format_html('<span style="color: red;">🗑️ Deleted</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">✅ Active</span>')
        else:
            return format_html('<span style="color: orange;">⏸️ Inactive</span>')
    status_display.short_description = "Status"
    
    actions = ['restore_farms', 'soft_delete_farms', 'activate_farms', 'deactivate_farms']
    
    def restore_farms(self, request, queryset):
        """Restore selected soft-deleted farms"""
        count = 0
        for farm in queryset:
            if farm.is_deleted:
                farm.restore()
                count += 1
        self.message_user(request, f'{count} farms restored successfully.')
    restore_farms.short_description = "Restore selected farms"
    
    def soft_delete_farms(self, request, queryset):
        """Soft delete selected farms"""
        count = 0
        for farm in queryset:
            if not farm.is_deleted:
                farm.soft_delete()
                count += 1
        self.message_user(request, f'{count} farms soft deleted successfully.')
    soft_delete_farms.short_description = "Soft delete selected farms"
    
    def activate_farms(self, request, queryset):
        """Activate selected farms"""
        count = queryset.filter(is_active=False, deleted_at__isnull=True).update(is_active=True)
        self.message_user(request, f'{count} farms activated successfully.')
    activate_farms.short_description = "Activate selected farms"
    
    def deactivate_farms(self, request, queryset):
        """Deactivate selected farms"""
        count = queryset.filter(is_active=True, deleted_at__isnull=True).update(is_active=False)
        self.message_user(request, f'{count} farms deactivated successfully.')
    deactivate_farms.short_description = "Deactivate selected farms"
    
    def get_queryset(self, request):
        """Include soft-deleted farms in admin"""
        return Farm.objects.all()

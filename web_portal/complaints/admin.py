# from django.contrib import admin
# from .models import Complaint

# @admin.register(Complaint)
# class ComplaintAdmin(admin.ModelAdmin):
#     list_display = ['complaint_id', 'user', 'status', 'created_at']
#     search_fields = ['complaint_id', 'user__username', 'message']
#     list_filter = ['status', 'created_at']
#     readonly_fields = ['status']  # ✅ Makes status uneditable

import uuid
from django.contrib import admin
from django.utils.html import format_html
from .models import Complaint

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = [
        'complaint_id', 'user', 'status', 'message', 'created_at', 'image_tag'
    ]
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['complaint_id', 'user__username', 'message']
    ordering = ['-created_at']
    
    readonly_fields = ['complaint_id', 'created_at', 'image_preview']
    
    fieldsets = (
        ('Basic Info', {'fields': ('complaint_id', 'user', 'message')}),
        ('Status & Timestamps', {'fields': ('status', 'created_at')}),
        ('Attachment', {'fields': ('image', 'image_preview')}),
    )
    
    def save_model(self, request, obj, form, change):
        # Auto-generate complaint_id if not set
        if not obj.complaint_id:
            obj.complaint_id = f"FB{uuid.uuid4().hex[:8].upper()}"
        super().save_model(request, obj, form, change)
    
    # Display image thumbnail in list
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Image'

    # Display image preview in form
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="200" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'

    # Permissions
    def has_change_permission(self, request, obj=None):
        if not request.user.is_staff:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_staff:
            return False
        return super().has_delete_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        if request.user.is_staff:
            return True
        if obj is not None:
            return obj.user == request.user
        return True
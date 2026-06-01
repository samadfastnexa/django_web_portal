# from django.contrib import admin
# from .models import Complaint

# @admin.register(Complaint)
# class ComplaintAdmin(admin.ModelAdmin):
#     list_display = ['complaint_id', 'user', 'status', 'created_at']
#     search_fields = ['complaint_id', 'user__username', 'message']
#     list_filter = ['status', 'created_at']
#     readonly_fields = ['status']  # ✅ Makes status uneditable

import json
import uuid
from django.contrib import admin
from django.db.models import Q
from web_portal.admin import admin_site
from django.utils.html import format_html
from .models import Complaint


_NOIMG_PLACEHOLDER = (
    '<div style="width:{w}px;height:{h}px;background:#e5e7eb;color:#6b7280;'
    'font-size:{fs}px;display:flex;align-items:center;justify-content:center;'
    'border:1px solid #d1d5db;border-radius:4px;text-align:center;line-height:1.1;'
    '">No image</div>'
)


def _img_with_fallback(url, w, h, fs):
    """<img> that swaps itself for a 'No image' tile if the file 404s."""
    placeholder_html = _NOIMG_PLACEHOLDER.format(w=w, h=h, fs=fs)
    onerror = 'this.outerHTML=' + json.dumps(placeholder_html) + ';'
    return format_html(
        '<img src="{}" width="{}" height="{}" '
        'style="object-fit:cover;border-radius:4px;" onerror="{}" />',
        url, w, h, onerror,
    )


class UserSearchFilter(admin.SimpleListFilter):
    """
    Sidebar 'By user' filter that scales beyond list-of-all-users. Renders a
    plain text input — the admin types part of a username/email/first/last
    name and submits. No JS dependency (avoids the Select2/noConflict race
    on the changelist).
    """
    title = 'user'
    parameter_name = 'user_q'
    template = 'admin/complaints/filter_user_search.html'

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        # Stash GET so the template can preserve other filter params when
        # submitting / clearing (admin_list_filter doesn't pass `request`
        # into the filter template context).
        self._get_items = list(request.GET.lists())

    @property
    def other_get_items(self):
        skip = {self.parameter_name, 'p'}
        return [(k, v) for k, v in self._get_items if k not in skip]

    def lookups(self, request, model_admin):
        return ()

    def has_output(self):
        return True

    def choices(self, changelist):
        # Suppress Django's default 'All / Any' rendering — the template
        # provides its own input and clear link.
        return []

    def queryset(self, request, queryset):
        val = (self.value() or '').strip()
        if not val:
            return queryset
        return queryset.filter(
            Q(user__username__icontains=val) |
            Q(user__email__icontains=val) |
            Q(user__first_name__icontains=val) |
            Q(user__last_name__icontains=val)
        )


@admin.register(Complaint, site=admin_site)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = [
        'complaint_id', 'user', 'status', 'message', 'created_at', 'image_tag'
    ]
    list_filter = ['status', 'created_at', UserSearchFilter]
    search_fields = ['complaint_id', 'user__username', 'user__email', 'user__first_name', 'user__last_name', 'message']
    autocomplete_fields = ['user']
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
    
    # Display image thumbnail in list (with fallback if the file is missing).
    def image_tag(self, obj):
        if not obj.image:
            return format_html(_NOIMG_PLACEHOLDER.format(w=50, h=50, fs=9))
        try:
            url = obj.image.url
        except Exception:
            return format_html(_NOIMG_PLACEHOLDER.format(w=50, h=50, fs=9))
        return _img_with_fallback(url, 50, 50, 9)
    image_tag.short_description = 'Image'

    # Display image preview in form (with fallback if the file is missing).
    def image_preview(self, obj):
        if not obj.image:
            return format_html(_NOIMG_PLACEHOLDER.format(w=200, h=200, fs=14))
        try:
            url = obj.image.url
        except Exception:
            return format_html(_NOIMG_PLACEHOLDER.format(w=200, h=200, fs=14))
        return _img_with_fallback(url, 200, 200, 14)
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
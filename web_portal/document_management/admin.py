from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Attachment, AttachmentAssignment, AttachmentDownloadLog


class AttachmentAssignmentInline(admin.TabularInline):
    """Inline admin for attachment assignments."""
    model = AttachmentAssignment
    extra = 1
    readonly_fields = ['assigned_at', 'viewed', 'viewed_at', 'download_count', 'last_downloaded_at']
    raw_id_fields = ['user', 'assigned_by']
    fields = [
        'user',
        'assigned_by',
        'assigned_at',
        'viewed',
        'viewed_at',
        'download_count',
        'acknowledged',
        'notes',
    ]


class AttachmentDownloadLogInline(admin.TabularInline):
    """Inline admin for download logs."""
    model = AttachmentDownloadLog
    extra = 0
    readonly_fields = ['downloaded_at', 'ip_address', 'user_agent']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class AttachmentAdmin(admin.ModelAdmin):
    """Admin interface for Attachment model."""
    
    list_display = [
        'title',
        'file_type_badge',
        'file_size_display',
        'status_badge',
        'created_by_link',
        'assigned_count',
        'viewed_count',
        'created_at',
        'expiry_status',
    ]
    
    list_filter = [
        'status',
        'file_type',
        'is_mandatory',
        'created_at',
        'expiry_date',
    ]
    
    search_fields = [
        'title',
        'description',
        'tags',
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name',
    ]
    
    readonly_fields = [
        'created_by',
        'created_at',
        'updated_at',
        'file_size',
        'file_type',
        'formatted_file_size',
        'is_expired',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title',
                'description',
                'file',
                'status',
            )
        }),
        ('File Details', {
            'fields': (
                'file_type',
                'file_size',
                'formatted_file_size',
            ),
            'classes': ('collapse',),
        }),
        ('Settings', {
            'fields': (
                'is_mandatory',
                'expiry_date',
                'is_expired',
                'tags',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [AttachmentAssignmentInline]
    
    date_hierarchy = 'created_at'
    
    actions = [
        'mark_as_active',
        'mark_as_archived',
        'bulk_assign_users',
    ]
    
    def file_type_badge(self, obj):
        """Display file type as badge."""
        colors = {
            'pdf': '#d32f2f',
            'doc': '#1976d2',
            'docx': '#1976d2',
            'jpg': '#388e3c',
            'jpeg': '#388e3c',
            'png': '#388e3c',
        }
        color = colors.get(obj.file_type, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.file_type.upper()
        )
    file_type_badge.short_description = 'Type'
    
    def file_size_display(self, obj):
        """Display formatted file size."""
        return obj.formatted_file_size
    file_size_display.short_description = 'Size'
    
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            'active': '#4caf50',
            'archived': '#ff9800',
            'expired': '#f44336',
        }
        color = colors.get(obj.status, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def created_by_link(self, obj):
        """Link to creator's admin page."""
        if obj.created_by:
            url = reverse('admin:auth_user_change', args=[obj.created_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.created_by.username)
        return '-'
    created_by_link.short_description = 'Created By'
    
    def assigned_count(self, obj):
        """Count of assigned users."""
        count = obj.assigned_users.count()
        return format_html(
            '<span style="font-weight: bold; color: #1976d2;">{}</span>',
            count
        )
    assigned_count.short_description = 'Assigned'
    
    def viewed_count(self, obj):
        """Count of users who viewed."""
        total = obj.assignments.count()
        viewed = obj.assignments.filter(viewed=True).count()
        
        if total == 0:
            return '-'
        
        percentage = (viewed / total) * 100 if total > 0 else 0
        color = '#4caf50' if percentage > 70 else '#ff9800' if percentage > 30 else '#f44336'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{} ({}%)</span>',
            color,
            viewed,
            total,
            int(percentage)
        )
    viewed_count.short_description = 'Viewed'
    
    def expiry_status(self, obj):
        """Display expiry status."""
        if not obj.expiry_date:
            return format_html('<span style="color: #757575;">No expiry</span>')
        
        if obj.is_expired:
            return format_html(
                '<span style="color: #f44336; font-weight: bold;">Expired</span>'
            )
        
        days_left = (obj.expiry_date - timezone.now()).days
        if days_left <= 7:
            color = '#ff9800'
            text = f'Expires in {days_left} days'
        else:
            color = '#4caf50'
            text = f'Expires in {days_left} days'
        
        return format_html('<span style="color: {};">{}</span>', color, text)
    expiry_status.short_description = 'Expiry'
    
    def mark_as_active(self, request, queryset):
        """Bulk action to mark attachments as active."""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} attachment(s) marked as active.')
    mark_as_active.short_description = 'Mark selected as active'
    
    def mark_as_archived(self, request, queryset):
        """Bulk action to archive attachments."""
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} attachment(s) archived.')
    mark_as_archived.short_description = 'Mark selected as archived'
    
    def save_model(self, request, obj, form, change):
        """Set created_by on save."""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class AttachmentAssignmentAdmin(admin.ModelAdmin):
    """Admin interface for AttachmentAssignment model."""
    
    list_display = [
        'attachment_link',
        'user_link',
        'assigned_by_link',
        'assigned_at',
        'viewed_badge',
        'download_count_display',
        'acknowledged_badge',
    ]
    
    list_filter = [
        'viewed',
        'acknowledged',
        'assigned_at',
        'viewed_at',
    ]
    
    search_fields = [
        'attachment__title',
        'user__username',
        'user__first_name',
        'user__last_name',
        'assigned_by__username',
    ]
    
    readonly_fields = [
        'assigned_at',
        'viewed',
        'viewed_at',
        'download_count',
        'last_downloaded_at',
    ]
    
    raw_id_fields = ['attachment', 'user', 'assigned_by']
    
    fieldsets = (
        ('Assignment Details', {
            'fields': (
                'attachment',
                'user',
                'assigned_by',
                'assigned_at',
            )
        }),
        ('Tracking', {
            'fields': (
                'viewed',
                'viewed_at',
                'download_count',
                'last_downloaded_at',
            )
        }),
        ('Acknowledgment', {
            'fields': (
                'acknowledged',
                'acknowledged_at',
                'notes',
            )
        }),
    )
    
    inlines = [AttachmentDownloadLogInline]
    
    date_hierarchy = 'assigned_at'
    
    def attachment_link(self, obj):
        """Link to attachment."""
        url = reverse('admin:document_management_attachment_change', args=[obj.attachment.id])
        return format_html('<a href="{}">{}</a>', url, obj.attachment.title)
    attachment_link.short_description = 'Attachment'
    
    def user_link(self, obj):
        """Link to user."""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    
    def assigned_by_link(self, obj):
        """Link to assigner."""
        if obj.assigned_by:
            url = reverse('admin:auth_user_change', args=[obj.assigned_by.id])
            return format_html('<a href="{}">{}</a>', url, obj.assigned_by.username)
        return '-'
    assigned_by_link.short_description = 'Assigned By'
    
    def viewed_badge(self, obj):
        """Display viewed status."""
        if obj.viewed:
            return format_html(
                '<span style="color: #4caf50; font-weight: bold;">✓ Viewed</span>'
            )
        return format_html('<span style="color: #f44336;">✗ Not viewed</span>')
    viewed_badge.short_description = 'Viewed'
    
    def download_count_display(self, obj):
        """Display download count."""
        if obj.download_count > 0:
            return format_html(
                '<span style="font-weight: bold; color: #1976d2;">{}</span>',
                obj.download_count
            )
        return '0'
    download_count_display.short_description = 'Downloads'
    
    def acknowledged_badge(self, obj):
        """Display acknowledged status."""
        if obj.acknowledged:
            return format_html(
                '<span style="color: #4caf50; font-weight: bold;">✓ Yes</span>'
            )
        return format_html('<span style="color: #757575;">✗ No</span>')
    acknowledged_badge.short_description = 'Acknowledged'


class AttachmentDownloadLogAdmin(admin.ModelAdmin):
    """Admin interface for AttachmentDownloadLog model."""
    
    list_display = [
        'user_display',
        'attachment_display',
        'downloaded_at',
        'ip_address',
        'short_user_agent',
    ]
    
    list_filter = [
        'downloaded_at',
    ]
    
    search_fields = [
        'assignment__user__username',
        'assignment__attachment__title',
        'ip_address',
    ]
    
    readonly_fields = [
        'assignment',
        'downloaded_at',
        'ip_address',
        'user_agent',
    ]
    
    date_hierarchy = 'downloaded_at'
    
    def has_add_permission(self, request):
        """Prevent manual creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion (audit log)."""
        return False
    
    def user_display(self, obj):
        """Display user username."""
        return obj.assignment.user.username
    user_display.short_description = 'User'
    
    def attachment_display(self, obj):
        """Display attachment title."""
        return obj.assignment.attachment.title
    attachment_display.short_description = 'Attachment'
    
    def short_user_agent(self, obj):
        """Display shortened user agent."""
        if len(obj.user_agent) > 50:
            return obj.user_agent[:50] + '...'
        return obj.user_agent
    short_user_agent.short_description = 'User Agent'


# Register models with custom admin site
try:
    from web_portal.admin import admin_site
    admin_site.register(Attachment, AttachmentAdmin)
    admin_site.register(AttachmentAssignment, AttachmentAssignmentAdmin)
    admin_site.register(AttachmentDownloadLog, AttachmentDownloadLogAdmin)
except ImportError:
    # Fallback to default admin if custom admin_site not available
    admin.site.register(Attachment, AttachmentAdmin)
    admin.site.register(AttachmentAssignment, AttachmentAssignmentAdmin)
    admin.site.register(AttachmentDownloadLog, AttachmentDownloadLogAdmin)

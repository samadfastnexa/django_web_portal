from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import KindwiseIdentification
import json


@admin.register(KindwiseIdentification)
class KindwiseIdentificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_link', 'status_badge', 'image_name', 'created_at', 'view_details_link')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'image_name', 'source_ip')
    readonly_fields = ('id', 'user', 'image_name', 'request_payload_display', 'response_payload_display', 
                      'status', 'source_ip', 'user_agent', 'created_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'status', 'image_name', 'created_at')
        }),
        ('Request Information', {
            'fields': ('request_payload_display', 'source_ip', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('API Response', {
            'fields': ('response_payload_display',),
        }),
    )
    
    def user_link(self, obj):
        """Display user with link to user admin"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return format_html('<span style="color: #999;">N/A</span>')
    user_link.short_description = 'User'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        if obj.status == 'success':
            color = '#28a745'
            icon = '✓'
        elif obj.status == 'error':
            color = '#dc3545'
            icon = '✗'
        else:
            color = '#ffc107'
            icon = '?'
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: 600;">'
            '{} {}</span>',
            color, icon, obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def view_details_link(self, obj):
        """Link to view detailed response"""
        return format_html(
            '<a href="javascript:void(0)" onclick="showKindwiseDetails({})" '
            'style="background: #ff6600; color: white; padding: 5px 12px; border-radius: 4px; '
            'text-decoration: none; font-weight: 600;">View Details</a>',
            obj.pk
        )
    view_details_link.short_description = 'Actions'
    
    def request_payload_display(self, obj):
        """Display formatted request payload"""
        if not obj.request_payload:
            return format_html('<span style="color: #999;">No request data</span>')
        
        try:
            formatted = json.dumps(obj.request_payload, indent=2)
            return format_html(
                '<div style="'
                'max-height: 300px; '
                'overflow: auto; '
                'background: #f8f9fa; '
                'border: 2px solid #dee2e6; '
                'border-radius: 6px; '
                'padding: 12px; '
                'font-family: monospace; '
                'font-size: 13px; '
                'white-space: pre;'
                '">{}</div>',
                formatted
            )
        except:
            return str(obj.request_payload)
    request_payload_display.short_description = 'Request Payload'
    
    def response_payload_display(self, obj):
        """Display formatted response payload with scrollable container"""
        if not obj.response_payload:
            return format_html('<span style="color: #999;">No response data</span>')
        
        try:
            formatted = json.dumps(obj.response_payload, indent=2)
            
            # Extract key suggestions if available
            suggestions_html = ""
            if isinstance(obj.response_payload, dict):
                classification = obj.response_payload.get('classification', {})
                suggestions = classification.get('suggestions', [])
                
                if suggestions:
                    suggestions_html = '<div style="margin-bottom: 15px; padding: 15px; background: #e7f3ff; border-left: 4px solid #2196F3; border-radius: 4px;">'
                    suggestions_html += '<h4 style="margin: 0 0 10px 0; color: #1976D2;">🌱 Top Identifications</h4>'
                    for i, sug in enumerate(suggestions[:5]):  # Top 5
                        name = sug.get('name', 'Unknown')
                        prob = sug.get('probability', 0) * 100
                        suggestions_html += f'<div style="margin: 5px 0;"><strong>{i+1}. {name}</strong> - {prob:.1f}%</div>'
                    suggestions_html += '</div>'
            
            return format_html(
                '{}'
                '<div style="'
                'max-height: 500px; '
                'overflow: auto; '
                'background: #f8f9fa; '
                'border: 3px solid #ff6600; '
                'border-radius: 6px; '
                'padding: 12px; '
                'font-family: Consolas, Monaco, monospace; '
                'font-size: 13px; '
                'white-space: pre; '
                'line-height: 1.6;'
                '">{}</div>'
                '<style>'
                'div[style*="border: 3px solid #ff6600"]::-webkit-scrollbar {{ '
                'width: 14px; height: 14px; '
                '}} '
                'div[style*="border: 3px solid #ff6600"]::-webkit-scrollbar-track {{ '
                'background: #e0e0e0; '
                '}} '
                'div[style*="border: 3px solid #ff6600"]::-webkit-scrollbar-thumb {{ '
                'background: #ff6600; border: 3px solid #e0e0e0; '
                '}} '
                '</style>',
                mark_safe(suggestions_html),
                formatted
            )
        except:
            return str(obj.response_payload)
    response_payload_display.short_description = 'API Response'
    
    class Media:
        css = {
            'all': ('kindwise/admin/kindwise_admin.css',)
        }
        js = ('kindwise/admin/kindwise_admin.js',)
    
    def has_add_permission(self, request):
        """Disable adding records through admin (only via API)"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of records"""
        return request.user.is_superuser

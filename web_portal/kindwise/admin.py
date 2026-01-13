from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import KindwiseIdentification
from web_portal.admin import admin_site  # Use custom admin site
import json


@admin.register(KindwiseIdentification, site=admin_site)
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
        """Display formatted response payload in readable format with images"""
        if not obj.response_payload:
            return format_html('<span style="color: #999;">No response data</span>')
        
        try:
            response = obj.response_payload
            if not isinstance(response, dict):
                return str(obj.response_payload)
            
            html = ""
            result = response.get('result', {})
            
            # Crop Identification Section
            crop_data = result.get('crop', {})
            crop_suggestions = crop_data.get('suggestions', [])
            if crop_suggestions:
                html += '<div style="margin-bottom: 20px; padding: 18px; background: #e8f5e9; border-left: 5px solid #4CAF50; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">'
                html += '<h3 style="margin: 0 0 15px 0; color: #2e7d32; font-size: 18px; font-weight: 600;">🌾 Crop Identification</h3>'
                
                for i, sug in enumerate(crop_suggestions[:3]):  # Top 3
                    name = sug.get('name', 'Unknown')
                    scientific = sug.get('scientific_name', '')
                    prob = sug.get('probability', 0) * 100
                    
                    html += f'<div style="margin: 12px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #4CAF50; box-shadow: 0 1px 4px rgba(0,0,0,0.08);">'
                    html += f'<div style="font-size: 16px; font-weight: 600; color: #333; margin-bottom: 5px;">{i+1}. {name.title()}</div>'
                    if scientific:
                        html += f'<div style="color: #666; font-style: italic; font-size: 14px; margin: 4px 0;">{scientific}</div>'
                    html += f'<div style="margin-top: 8px;"><span style="background: #4CAF50; color: white; padding: 6px 14px; border-radius: 4px; font-weight: 600; font-size: 14px;">{prob:.1f}% Confidence</span></div>'
                    
                    # Similar images for crop
                    similar = sug.get('similar_images', [])
                    if similar:
                        html += '<div style="margin-top: 12px;">'
                        html += '<div style="color: #555; font-size: 13px; font-weight: 600; margin-bottom: 8px;">Similar Images:</div>'
                        html += '<div style="display: flex; gap: 10px; flex-wrap: wrap;">'
                        for img in similar[:3]:  # Show first 3 images
                            img_url = img.get('url_small') or img.get('url', '')
                            similarity = img.get('similarity', 0) * 100
                            citation = img.get('citation', 'Unknown')
                            if img_url:
                                html += f'<div style="position: relative;">'
                                html += f'<img src="{img_url}" style="width: 150px; height: 150px; object-fit: cover; border-radius: 5px; border: 2px solid #4CAF50; box-shadow: 0 2px 6px rgba(0,0,0,0.1);" title="{citation} - {similarity:.1f}% similar">'
                                html += f'<div style="position: absolute; bottom: 4px; right: 4px; background: rgba(0,0,0,0.8); color: white; padding: 3px 7px; border-radius: 3px; font-size: 11px; font-weight: 600;">{similarity:.0f}%</div>'
                                html += '</div>'
                        html += '</div></div>'
                    
                    html += '</div>'
                html += '</div>'
            
            # Disease Identification Section
            disease_data = result.get('disease', {})
            disease_suggestions = disease_data.get('suggestions', [])
            if disease_suggestions:
                html += '<div style="margin-bottom: 20px; padding: 18px; background: #fff3e0; border-left: 5px solid #FF9800; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">'
                html += '<h3 style="margin: 0 0 15px 0; color: #e65100; font-size: 18px; font-weight: 600;">🔬 Disease/Health Analysis</h3>'
                
                for i, sug in enumerate(disease_suggestions[:5]):  # Top 5
                    name = sug.get('name', 'Unknown')
                    scientific = sug.get('scientific_name', '')
                    prob = sug.get('probability', 0) * 100
                    
                    # Color code based on disease type
                    if name.lower() == 'healthy':
                        border_color = '#4CAF50'
                        bg_color = '#4CAF50'
                    else:
                        border_color = '#FF5722' if prob > 50 else '#FFC107'
                        bg_color = '#FF5722' if prob > 50 else '#FFC107'
                    
                    html += f'<div style="margin: 12px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid {border_color}; box-shadow: 0 1px 4px rgba(0,0,0,0.08);">'
                    html += f'<div style="font-size: 16px; font-weight: 600; color: #333; margin-bottom: 5px;">{i+1}. {name.title()}</div>'
                    if scientific and scientific.lower() != name.lower() and scientific != 'healthy':
                        html += f'<div style="color: #666; font-style: italic; font-size: 14px; margin: 4px 0;">{scientific}</div>'
                    html += f'<div style="margin-top: 8px;"><span style="background: {bg_color}; color: white; padding: 6px 14px; border-radius: 4px; font-weight: 600; font-size: 14px;">{prob:.1f}% Probability</span></div>'
                    
                    # Similar images for disease
                    similar = sug.get('similar_images', [])
                    if similar:
                        html += '<div style="margin-top: 12px;">'
                        html += '<div style="color: #555; font-size: 13px; font-weight: 600; margin-bottom: 8px;">Similar Cases:</div>'
                        html += '<div style="display: flex; gap: 10px; flex-wrap: wrap;">'
                        for img in similar[:3]:  # Show first 3 images
                            img_url = img.get('url_small') or img.get('url', '')
                            similarity = img.get('similarity', 0) * 100
                            citation = img.get('citation', 'Unknown')
                            if img_url:
                                html += f'<div style="position: relative;">'
                                html += f'<img src="{img_url}" style="width: 150px; height: 150px; object-fit: cover; border-radius: 5px; border: 2px solid {border_color}; box-shadow: 0 2px 6px rgba(0,0,0,0.1);" title="{citation} - {similarity:.1f}% similar">'
                                html += f'<div style="position: absolute; bottom: 4px; right: 4px; background: rgba(0,0,0,0.8); color: white; padding: 3px 7px; border-radius: 3px; font-size: 11px; font-weight: 600;">{similarity:.0f}%</div>'
                                html += '</div>'
                        html += '</div></div>'
                    
                    html += '</div>'
                html += '</div>'
            
            # Submitted Image
            input_data = response.get('input', {})
            images = input_data.get('images', [])
            if images and images[0]:
                html += '<div style="margin-bottom: 20px; padding: 18px; background: #f3e5f5; border-left: 5px solid #9C27B0; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);">'
                html += '<h3 style="margin: 0 0 15px 0; color: #6a1b9a; font-size: 18px; font-weight: 600;">📸 Submitted Image</h3>'
                html += f'<img src="{images[0]}" style="max-width: 400px; max-height: 400px; border-radius: 6px; border: 3px solid #9C27B0; box-shadow: 0 3px 10px rgba(0,0,0,0.12);">'
                html += '</div>'
            
            # Additional Info
            is_plant = result.get('is_plant', {})
            if is_plant:
                is_plant_binary = is_plant.get('binary', False)
                is_plant_prob = is_plant.get('probability', 0) * 100
                
                html += '<div style="margin-bottom: 12px; padding: 12px; background: #e3f2fd; border-left: 4px solid #2196F3; border-radius: 5px;">'
                html += f'<div style="color: #1565c0; font-size: 14px; font-weight: 600;"><strong>Is Plant:</strong> {"✓ Yes" if is_plant_binary else "✗ No"} ({is_plant_prob:.2f}% confidence)</div>'
                html += '</div>'
            
            return format_html('<div>{}</div>', mark_safe(html))
            
        except Exception as e:
            # Fallback to JSON display
            formatted = json.dumps(obj.response_payload, indent=2)
            return format_html(
                '<div style="color: #d32f2f; margin-bottom: 10px;">Error rendering display: {}</div>'
                '<div style="max-height: 500px; overflow: auto; background: #f8f9fa; border: 3px solid #ff6600; border-radius: 6px; padding: 12px; font-family: Consolas, Monaco, monospace; font-size: 13px; white-space: pre; line-height: 1.6;">{}</div>',
                str(e),
                formatted
            )
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

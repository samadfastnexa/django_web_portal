from django.contrib import admin
from .models import Crop, CropStage


class CropStageInline(admin.TabularInline):
    """Inline admin for crop stages"""
    model = CropStage
    extra = 1
    fields = ['stage_name', 'days_after_sowing', 'brand', 'active_ingredient', 'dose_per_acre', 'purpose']
    ordering = ['days_after_sowing']


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    """Admin interface for Crop model"""
    list_display = ['name', 'variety', 'season', 'stages_count', 'created_by', 'created_at']
    list_filter = ['season', 'created_at', 'created_by']
    search_fields = ['name', 'variety', 'remarks']
    readonly_fields = ['created_at']
    inlines = [CropStageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'variety', 'season')
        }),
        ('Additional Details', {
            'fields': ('remarks', 'created_by', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def stages_count(self, obj):
        """Display number of stages for each crop"""
        return obj.stages.count()
    stages_count.short_description = 'Stages'
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user if not set"""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CropStage)
class CropStageAdmin(admin.ModelAdmin):
    """Admin interface for CropStage model"""
    list_display = ['crop', 'stage_name', 'days_after_sowing', 'brand', 'active_ingredient', 'dose_per_acre']
    list_filter = ['crop', 'days_after_sowing']
    search_fields = ['crop__name', 'stage_name', 'brand', 'active_ingredient', 'purpose']
    autocomplete_fields = ['crop']
    
    fieldsets = (
        ('Stage Information', {
            'fields': ('crop', 'stage_name', 'days_after_sowing')
        }),
        ('Treatment Details', {
            'fields': ('brand', 'active_ingredient', 'dose_per_acre', 'purpose')
        })
    )
    
    ordering = ['crop__name', 'days_after_sowing']

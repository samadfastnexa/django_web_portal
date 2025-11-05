from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Crop, CropVariety, YieldData, FarmingPractice, CropResearch


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    """Admin interface for Crop model"""
    
    list_display = [
        'name', 'scientific_name', 'category', 'growth_season',
        'growth_cycle_days', 'water_requirement', 'varieties_count',
        'is_active', 'created_at'
    ]
    list_filter = [
        'category', 'growth_season', 'water_requirement',
        'is_active', 'created_at'
    ]
    search_fields = [
        'name', 'scientific_name', 'description',
        'market_availability', 'economic_importance'
    ]
    readonly_fields = ['created_at', 'updated_at', 'varieties_count']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'scientific_name', 'category', 'description')
        }),
        ('Growth Information', {
            'fields': (
                'growth_cycle_days', 'growth_season', 'water_requirement',
                'soil_type_preference', 'climate_requirement'
            )
        }),
        ('Additional Information', {
            'fields': ('nutritional_value', 'market_availability', 'economic_importance'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    ordering = ['name']
    date_hierarchy = 'created_at'
    
    def varieties_count(self, obj):
        """Display count of varieties for this crop"""
        count = obj.varieties.count()
        if count > 0:
            url = reverse('admin:crop_management_cropvariety_changelist')
            return format_html(
                '<a href="{}?crop__id__exact={}">{} varieties</a>',
                url, obj.id, count
            )
        return '0 varieties'
    varieties_count.short_description = 'Varieties'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related"""
        return super().get_queryset(request).prefetch_related('varieties')


@admin.register(CropVariety)
class CropVarietyAdmin(admin.ModelAdmin):
    """Admin interface for CropVariety model"""
    
    list_display = [
        'name', 'variety_code', 'crop', 'yield_potential',
        'maturity_days', 'seed_availability', 'release_year',
        'is_active', 'created_at'
    ]
    list_filter = [
        'crop', 'seed_availability', 'release_year',
        'is_active', 'created_at'
    ]
    search_fields = [
        'name', 'variety_code', 'crop__name', 'description',
        'developed_by', 'special_requirements'
    ]
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['crop']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'variety_code', 'crop', 'description')
        }),
        ('Performance Data', {
            'fields': (
                'yield_potential', 'maturity_days', 'quality_attributes',
                'disease_resistance', 'pest_resistance'
            )
        }),
        ('Development Information', {
            'fields': (
                'developed_by', 'release_year', 'seed_availability',
                'special_requirements', 'recommended_regions'
            )
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    ordering = ['crop__name', 'name']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('crop')


@admin.register(YieldData)
class YieldDataAdmin(admin.ModelAdmin):
    """Admin interface for YieldData model"""
    
    list_display = [
        'crop', 'variety', 'farm', 'harvest_year', 'harvest_season',
        'yield_per_hectare', 'total_yield', 'area_cultivated',
        'quality_grade', 'profit_margin', 'created_at'
    ]
    list_filter = [
        'crop', 'variety', 'harvest_year', 'harvest_season',
        'quality_grade', 'created_at'
    ]
    search_fields = [
        'crop__name', 'variety__name', 'farm__name',
        'notes', 'data_source'
    ]
    readonly_fields = ['created_at', 'updated_at', 'profit_margin']
    autocomplete_fields = ['crop', 'variety', 'farm']
    fieldsets = (
        ('Basic Information', {
            'fields': ('crop', 'variety', 'farm', 'harvest_year', 'harvest_season')
        }),
        ('Yield Data', {
            'fields': (
                'area_cultivated', 'total_yield', 'yield_per_hectare',
                'quality_grade'
            )
        }),
        ('Environmental Conditions', {
            'fields': (
                'rainfall_mm', 'temperature_avg'
            ),
            'classes': ('collapse',)
        }),
        ('Economic Data', {
            'fields': (
                'input_cost', 'market_price', 'profit_margin'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'data_source'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    ordering = ['-harvest_year', 'crop__name']
    date_hierarchy = 'created_at'
    
    def profit_margin(self, obj):
        """Calculate and display profit margin"""
        if obj.market_price and obj.input_cost:
            margin = ((obj.market_price - obj.input_cost) / obj.market_price) * 100
            color = 'green' if margin > 0 else 'red'
            return format_html(
                '<span style="color: {};">{}</span>',
                str(color), f"{float(margin):.1f}%"
            )
        return '-'
    profit_margin.short_description = 'Profit Margin'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'crop', 'variety', 'farm'
        )


@admin.register(FarmingPractice)
class FarmingPracticeAdmin(admin.ModelAdmin):
    """Admin interface for FarmingPractice model"""
    
    list_display = [
        'title', 'crop', 'variety', 'practice_type',
        'validation_status', 'priority_level', 'estimated_cost',
        'is_active', 'created_at'
    ]
    list_filter = [
        'crop', 'practice_type', 'validation_status',
        'priority_level', 'labor_requirement', 'is_active', 'created_at'
    ]
    search_fields = [
        'title', 'description', 'crop__name', 'variety__name',
        'research_source', 'implementation_steps'
    ]
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['crop', 'variety']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'crop', 'variety', 'practice_type', 'description')
        }),
        ('Implementation Details', {
            'fields': (
                'implementation_steps', 'required_materials',
                'days_after_planting', 'timing_description'
            )
        }),
        ('Resource Requirements', {
            'fields': (
                'estimated_cost', 'labor_requirement'
            ),
            'classes': ('collapse',)
        }),
        ('Validation & Research', {
            'fields': (
                'validation_status', 'priority_level', 'research_source',
                'expected_impact', 'success_indicators'
            ),
            'classes': ('collapse',)
        }),
        ('Regional Information', {
            'fields': ('applicable_regions', 'climate_suitability'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    ordering = ['crop__name', 'practice_type', 'title']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'crop', 'variety'
        )


@admin.register(CropResearch)
class CropResearchAdmin(admin.ModelAdmin):
    """Admin interface for CropResearch model"""
    
    list_display = [
        'title', 'crop', 'variety', 'research_type',
        'research_institution', 'principal_investigator',
        'publication_status', 'research_duration', 'created_at'
    ]
    list_filter = [
        'crop', 'research_type', 'research_institution',
        'publication_status', 'research_period_start', 'created_at'
    ]
    search_fields = [
        'title', 'objective', 'crop__name', 'variety__name',
        'research_institution', 'principal_investigator',
        'publication_reference', 'doi'
    ]
    readonly_fields = ['created_at', 'updated_at', 'research_duration']
    autocomplete_fields = ['crop', 'variety']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'crop', 'variety', 'research_type',
                'objective'
            )
        }),
        ('Research Details', {
            'fields': (
                'research_institution', 'principal_investigator',
                'research_period_start', 'research_period_end',
                'research_duration', 'methodology'
            )
        }),
        ('Results & Findings', {
            'fields': (
                'findings', 'conclusions',
                'practical_applications'
            ),
            'classes': ('collapse',)
        }),
        ('Publication Information', {
            'fields': (
                'publication_status', 'publication_reference',
                'doi', 'research_document'
            ),
            'classes': ('collapse',)
        }),
        ('Impact & Collaboration', {
            'fields': (
                'impact_assessment',
            ),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    ordering = ['-research_period_start', 'crop__name']
    date_hierarchy = 'research_period_start'
    
    def research_duration(self, obj):
        """Calculate and display research duration"""
        if obj.research_period_start and obj.research_period_end:
            duration = obj.research_period_end - obj.research_period_start
            return f"{str(duration.days)} days"
        elif obj.research_period_start:
            from django.utils import timezone
            duration = timezone.now().date() - obj.research_period_start
            return f"{str(duration.days)} days (ongoing)"
        return '-'
    research_duration.short_description = 'Duration'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'crop', 'variety'
        )


# # Custom admin site configuration
# admin.site.site_header = "Tarzan Admin Panel by Fastnexa"
# admin.site.site_title = "Tarzan Management Admin"
# admin.site.index_title = "Welcome to Tarzan by Fastnexa"

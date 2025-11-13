from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.urls import path
from django.http import HttpResponse
from django.contrib import messages
from io import BytesIO
from .exports import build_trials_workbook, build_trials_pdf
from .models import (
    Crop, CropStage, Trial, TrialTreatment, TrialImage,
    Product, CropStageImage, Pest, PestManagementGuideline,
    TrialInitCondition, EnvironmentalCondition, SpeciesPerformanceObservation,
    DoseResponseObservation, ComparativePerformance, Recommendation, TrialRepetitionPlan
)


class CropStageInline(admin.TabularInline):
    """Inline admin for crop stages"""
    model = CropStage
    extra = 1
    fields = ['stage_name', 'days_after_sowing', 'brand', 'active_ingredient', 'dose_per_acre', 'purpose', 'remarks', 'images_link']
    readonly_fields = ['images_link']
    ordering = ['days_after_sowing']

    def images_link(self, obj):
        if not obj or not getattr(obj, 'pk', None):
            return ""
        count = obj.images.count()
        url = reverse('admin:crop_manage_cropstageimage_changelist')
        return format_html('<a href="{}?crop_stage__id__exact={}">Manage images ({})</a>', url, obj.pk, count)


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    """Admin interface for Crop model"""
    list_display = ['name', 'variety', 'season', 'stages_count', 'created_by', 'created_at']
    list_filter = ['season', 'created_at', 'created_by']
    search_fields = ['name', 'variety', 'remarks']
    readonly_fields = ['created_at']
    class PestGuidelineInline(admin.TabularInline):
        model = PestManagementGuideline
        extra = 1
        autocomplete_fields = ['pest', 'products']
        fields = [
            'pest', 'control_category', 'type_label', 'time_of_application',
            'water_volume', 'nozzles', 'number_of_applications', 'observation_time',
            'method_of_application', 'method_of_observation', 'trial_starting_stage', 'products'
        ]
        show_change_link = True

    inlines = [CropStageInline, PestGuidelineInline]
    
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
    list_display = ['crop', 'stage_name', 'days_after_sowing', 'brand', 'active_ingredient', 'dose_per_acre', 'has_images']
    list_filter = ['crop', 'days_after_sowing']
    search_fields = ['crop__name', 'stage_name', 'brand', 'active_ingredient', 'purpose', 'remarks']
    autocomplete_fields = ['crop']
    
    fieldsets = (
        ('Stage Information', {
            'fields': ('crop', 'stage_name', 'days_after_sowing')
        }),
        ('Treatment Details', {
            'fields': ('brand', 'active_ingredient', 'dose_per_acre', 'purpose', 'remarks')
        })
    )
    
    ordering = ['crop__name', 'days_after_sowing']

    class CropStageImageInline(admin.TabularInline):
        model = CropStageImage
        extra = 3
        fields = ['image', 'caption', 'taken_at', 'preview']
        readonly_fields = ['preview']

        def preview(self, obj):
            if obj and getattr(obj, 'image', None):
                try:
                    return format_html('<img src="{}" style="width:120px;height:90px;object-fit:cover;border:1px solid #ccc;" />', obj.image.url)
                except Exception:
                    return ""
            return ""

    inlines = [CropStageImageInline]

    def has_images(self, obj):
        return obj.images.count() > 0
    has_images.boolean = True
    has_images.short_description = 'Images?'


@admin.register(Trial)
class TrialAdmin(admin.ModelAdmin):
    """Admin interface for Trial model (separate from crops)."""
    list_display = [
        'station', 'trial_name', 'location_area', 'crop_variety',
        'application_date', 'design_replicates', 'water_volume_used'
    ]
    list_filter = ['station', 'application_date']
    search_fields = ['station', 'trial_name', 'location_area', 'crop_variety']
    readonly_fields = ['created_at']
    change_list_template = 'admin/crop_manage/trial/change_list.html'

    # -------- Export helpers --------
    actions = ['export_selected_xlsx', 'export_selected_pdf']

    def export_selected_xlsx(self, request, queryset):
        """Export selected trials (and their treatments) to XLSX using builder."""
        try:
            treatments = TrialTreatment.objects.select_related('trial', 'product').filter(trial__in=queryset)
            output = build_trials_workbook(queryset, treatments)
        except RuntimeError as e:
            return HttpResponse(str(e), status=500, content_type='text/plain')
        resp = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = 'attachment; filename="trials_selected.xlsx"'
        return resp
    export_selected_xlsx.short_description = 'Export selected trials to XLSX'

    def export_selected_pdf(self, request, queryset):
        """Export selected trials (and their treatments) to PDF using builder."""
        try:
            treatments = TrialTreatment.objects.select_related('trial', 'product').filter(trial__in=queryset)
            buffer = build_trials_pdf(queryset, treatments)
        except RuntimeError as e:
            return HttpResponse(str(e), status=500, content_type='text/plain')
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = 'attachment; filename="trials_selected.pdf"'
        return resp
    export_selected_pdf.short_description = 'Export selected trials to PDF'

    # Custom admin URLs for Export All
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('export/xlsx/', self.admin_site.admin_view(self.export_all_xlsx), name='trial_export_xlsx'),
            path('export/pdf/', self.admin_site.admin_view(self.export_all_pdf), name='trial_export_pdf'),
        ]
        return custom + urls

    def export_all_xlsx(self, request):
        try:
            trials = Trial.objects.all()
            treatments = TrialTreatment.objects.select_related('trial', 'product').all()
            output = build_trials_workbook(trials, treatments)
        except RuntimeError as e:
            return HttpResponse(str(e), status=500, content_type='text/plain')
        resp = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = 'attachment; filename="trials_all.xlsx"'
        return resp

    def export_all_pdf(self, request):
        try:
            trials = Trial.objects.all()
            treatments = TrialTreatment.objects.select_related('trial', 'product').all()
            buffer = build_trials_pdf(trials, treatments)
        except RuntimeError as e:
            return HttpResponse(str(e), status=500, content_type='text/plain')
        resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = 'attachment; filename="trials_all.pdf"'
        return resp

    # Friendly tip for users on changelist
    def changelist_view(self, request, extra_context=None):
        if not request.session.get('trial_export_tip_shown'):
            messages.info(request, 'Tip: Use Actions to export selected trials, or the Export All buttons at the top to download the full report in XLSX or PDF.')
            request.session['trial_export_tip_shown'] = True
        return super().changelist_view(request, extra_context=extra_context)
    
    class TrialTreatmentInline(admin.TabularInline):
        model = TrialTreatment
        extra = 1
        fields = [
            'label', 'product', 'crop_stage_soil', 'pest_stage_start',
            'crop_safety_stress_rating', 'details',
            'growth_improvement_type', 'best_dose', 'others', 'images_link'
        ]
        autocomplete_fields = ['product']
        readonly_fields = ['images_link']
        show_change_link = True

        def images_link(self, obj):
            if not obj or not getattr(obj, 'pk', None):
                return ""
            count = obj.images.count()
            url = reverse('admin:crop_manage_trialimage_changelist')
            return format_html('<a href="{}?treatment__id__exact={}">Manage images ({})</a>', url, obj.pk, count)

    class TrialInitConditionInline(admin.StackedInline):
        model = TrialInitCondition
        extra = 0
        max_num = 1
        fields = ['crop_health_ok', 'weed_growth_stage', 'meets_requirements', 'notes']

    fieldsets = (
        ('Station / Trial', {
            'fields': ('station', 'trial_name')
        }),
        ('Location & Crop', {
            'fields': ('location_area', 'crop_variety')
        }),
        ('Application & Design', {
            'fields': ('application_date', 'design_replicates')
        }),
        ('Operational', {
            'fields': ('water_volume_used', 'previous_sprays')
        }),
        ('Weather Info', {
            'fields': (
                'temp_min_c', 'temp_max_c',
                'humidity_min_percent', 'humidity_max_percent',
                'wind_velocity_kmh', 'rainfall'
            )
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    inlines = [TrialTreatmentInline, TrialInitConditionInline]


@admin.register(TrialTreatment)
class TrialTreatmentAdmin(admin.ModelAdmin):
    list_display = ['trial', 'label', 'product', 'best_dose']
    search_fields = ['trial__station', 'trial__trial_name', 'label', 'product__name', 'product__brand']
    autocomplete_fields = ['product']

    class TrialImageInline(admin.TabularInline):
        model = TrialImage
        extra = 3
        fields = ['image_type', 'image', 'caption', 'taken_at', 'preview']
        readonly_fields = ['preview']

        def preview(self, obj):
            if obj and getattr(obj, 'image', None):
                try:
                    return format_html('<img src="{}" style="width:120px;height:90px;object-fit:cover;border:1px solid #ccc;" />', obj.image.url)
                except Exception:
                    return ""
            return ""

    class EnvironmentalConditionInline(admin.TabularInline):
        model = EnvironmentalCondition
        extra = 0
        fields = ['temperature_c', 'humidity_pct', 'wind_speed_kmh', 'soil_moisture_pct', 'rainfall_24h_mm', 'notes']

    class SpeciesPerformanceObservationInline(admin.TabularInline):
        model = SpeciesPerformanceObservation
        extra = 0
        autocomplete_fields = ['pest']
        fields = ['pest', 'observation_day', 'control_efficacy_pct', 'method', 'dose_ml_per_acre', 'notes']

    class DoseResponseObservationInline(admin.TabularInline):
        model = DoseResponseObservation
        extra = 0
        fields = ['dose_ml_per_acre', 'observation_day', 'efficacy_pct', 'notes']

    class ComparativePerformanceInline(admin.TabularInline):
        model = ComparativePerformance
        extra = 0
        autocomplete_fields = ['reference_product']
        fields = ['reference_product', 'observation_day', 'efficacy_pct', 'notes']

    inlines = [
        TrialImageInline,
        EnvironmentalConditionInline,
        SpeciesPerformanceObservationInline,
        DoseResponseObservationInline,
        ComparativePerformanceInline,
    ]


@admin.register(TrialImage)
class TrialImageAdmin(admin.ModelAdmin):
    list_display = ['treatment', 'image_type', 'thumbnail', 'uploaded_at']
    list_filter = ['image_type', 'uploaded_at', 'treatment__trial__station', 'treatment__trial__trial_name']
    search_fields = ['treatment__label', 'treatment__trial__station', 'treatment__trial__trial_name', 'caption']
    autocomplete_fields = ['treatment']

    def thumbnail(self, obj):
        if obj and getattr(obj, 'image', None):
            try:
                return format_html('<img src="{}" style="width:80px;height:60px;object-fit:cover;border:1px solid #ccc;" />', obj.image.url)
            except Exception:
                return ""
        return ""
    thumbnail.short_description = 'Preview'
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'active_ingredient', 'formulation']
    search_fields = ['name', 'brand', 'active_ingredient']
    list_filter = ['brand']
@admin.register(CropStageImage)
class CropStageImageAdmin(admin.ModelAdmin):
    list_display = ['crop_stage', 'thumbnail', 'taken_at', 'uploaded_at']
    list_filter = ['taken_at', 'uploaded_at', 'crop_stage__crop__name']
    search_fields = ['crop_stage__stage_name', 'crop_stage__crop__name', 'caption']
    autocomplete_fields = ['crop_stage']

    def thumbnail(self, obj):
        if obj and getattr(obj, 'image', None):
            try:
                return format_html('<img src="{}" style="width:80px;height:60px;object-fit:cover;border:1px solid #ccc;" />', obj.image.url)
            except Exception:
                return ""
        return ""
    thumbnail.short_description = 'Preview'
@admin.register(Pest)
class PestAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'species_group']
    list_filter = ['category']
    search_fields = ['name', 'species_group', 'notes']


@admin.register(PestManagementGuideline)
class PestManagementGuidelineAdmin(admin.ModelAdmin):
    list_display = [
        'pest', 'control_category', 'type_label', 'crop', 'time_of_application', 'water_volume', 'nozzles', 'number_of_applications'
    ]
    list_filter = ['control_category', 'crop', 'pest']
    search_fields = [
        'type_label', 'time_of_application', 'observation_time',
        'method_of_application', 'method_of_observation', 'trial_starting_stage'
    ]
    autocomplete_fields = ['crop', 'pest', 'products']

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['product', 'crop', 'pest', 'recommended_dose_ml_per_acre', 'source_trial']
    list_filter = ['crop', 'pest']
    search_fields = ['basis', 'success_metrics', 'product__name']
    autocomplete_fields = ['product', 'crop', 'pest', 'source_trial']

@admin.register(TrialRepetitionPlan)
class TrialRepetitionPlanAdmin(admin.ModelAdmin):
    list_display = ['product', 'crop', 'pest', 'dose_min_ml_per_acre', 'dose_max_ml_per_acre', 'status']
    list_filter = ['status', 'crop', 'pest']
    search_fields = ['success_metrics', 'notes', 'product__name']
    autocomplete_fields = ['product', 'crop', 'pest']

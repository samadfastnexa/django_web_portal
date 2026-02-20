from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from farm.models import Farm

User = get_user_model()

class Crop(models.Model):
    """Main crop model for tracking different crops"""
    
    CROP_CATEGORIES = [
        ('cereal', _('Cereal')),
        ('vegetable', _('Vegetable')),
        ('fruit', _('Fruit')),
        ('legume', _('Legume')),
        ('oilseed', _('Oilseed')),
        ('fiber', _('Fiber')),
        ('spice', _('Spice')),
        ('medicinal', _('Medicinal')),
        ('fodder', _('Fodder')),
        ('other', _('Other')),
    ]
    
    GROWTH_SEASONS = [
        ('kharif', _('Kharif (Summer)')),
        ('rabi', _('Rabi (Winter)')),
        ('zaid', _('Zaid (Spring)')),
        ('perennial', _('Perennial')),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Crop Name'))
    scientific_name = models.CharField(max_length=150, blank=True, verbose_name=_('Scientific Name'))
    category = models.CharField(max_length=20, choices=CROP_CATEGORIES, verbose_name=_('Category'))
    growth_season = models.CharField(max_length=20, choices=GROWTH_SEASONS, verbose_name=_('Growth Season'))
    
    # Growth cycle information
    growth_cycle_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text=_('Number of days from planting to harvest'),
        verbose_name=_('Growth Cycle (Days)')
    )
    
    # Market and economic data
    market_availability = models.TextField(blank=True, verbose_name=_('Market Availability'))
    economic_importance = models.TextField(blank=True, verbose_name=_('Economic Importance'))
    
    # Agricultural requirements
    water_requirement = models.CharField(
        max_length=20,
        choices=[('low', _('Low')), ('medium', _('Medium')), ('high', _('High'))],
        default='medium',
        verbose_name=_('Water Requirement')
    )
    
    soil_type_preference = models.TextField(blank=True, verbose_name=_('Soil Type Preference'))
    climate_requirement = models.TextField(blank=True, verbose_name=_('Climate Requirement'))
    
    # Metadata
    description = models.TextField(blank=True, verbose_name=_('Description'))
    nutritional_value = models.JSONField(default=dict, blank=True, verbose_name=_('Nutritional Value'))
    
    # Tracking fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_crops')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'crop_management_crop'
        verbose_name = _('Crop')
        verbose_name_plural = _('Crops')
        ordering = ['name']
    
    def __str__(self):
        return f"{str(self.name)} ({str(self.get_category_display())})"


class CropVariety(models.Model):
    """Different varieties of crops with specific characteristics"""
    
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='varieties')
    name = models.CharField(max_length=100, verbose_name=_('Variety Name'))
    variety_code = models.CharField(max_length=50, unique=True, verbose_name=_('Variety Code'))
    
    # Characteristics
    yield_potential = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text=_('Expected yield per hectare (kg/ha)'),
        verbose_name=_('Yield Potential (kg/ha)')
    )
    
    maturity_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_('Days to maturity from planting'),
        verbose_name=_('Maturity Days')
    )
    
    disease_resistance = models.TextField(blank=True, verbose_name=_('Disease Resistance'))
    pest_resistance = models.TextField(blank=True, verbose_name=_('Pest Resistance'))
    
    # Quality attributes
    quality_attributes = models.JSONField(default=dict, blank=True, verbose_name=_('Quality Attributes'))
    
    # Cultivation requirements
    special_requirements = models.TextField(blank=True, verbose_name=_('Special Requirements'))
    recommended_regions = models.TextField(blank=True, verbose_name=_('Recommended Regions'))
    
    # Availability
    seed_availability = models.CharField(
        max_length=20,
        choices=[('available', _('Available')), ('limited', _('Limited')), ('unavailable', _('Unavailable'))],
        default='available',
        verbose_name=_('Seed Availability')
    )
    
    # Metadata
    description = models.TextField(blank=True, verbose_name=_('Description'))
    developed_by = models.CharField(max_length=200, blank=True, verbose_name=_('Developed By'))
    release_year = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Release Year'))
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'crop_management_cropvariety'
        verbose_name = _('Crop Variety')
        verbose_name_plural = _('Crop Varieties')
        unique_together = ['crop', 'name']
        ordering = ['crop__name', 'name']
    
    def __str__(self):
        return f"{str(self.crop.name)} - {str(self.name)}"


class YieldData(models.Model):
    """Historical yield data for crops across different farms"""
    
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='yield_records')
    variety = models.ForeignKey(CropVariety, on_delete=models.CASCADE, null=True, blank=True, related_name='yield_records')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='crop_yields')
    
    # Yield information
    harvest_year = models.PositiveIntegerField(verbose_name=_('Harvest Year'))
    harvest_season = models.CharField(
        max_length=20,
        choices=Crop.GROWTH_SEASONS,
        verbose_name=_('Harvest Season')
    )
    
    area_cultivated = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text=_('Area cultivated in hectares'),
        verbose_name=_('Area Cultivated (ha)')
    )
    
    total_yield = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text=_('Total yield in kilograms'),
        verbose_name=_('Total Yield (kg)')
    )
    
    yield_per_hectare = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text=_('Calculated yield per hectare'),
        verbose_name=_('Yield per Hectare (kg/ha)')
    )
    
    # Quality metrics
    quality_grade = models.CharField(
        max_length=10,
        choices=[('A', _('Grade A')), ('B', _('Grade B')), ('C', _('Grade C'))],
        null=True, blank=True,
        verbose_name=_('Quality Grade')
    )
    
    # Environmental factors
    rainfall_mm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        verbose_name=_('Rainfall (mm)')
    )
    
    temperature_avg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_('Average Temperature (°C)')
    )
    
    # Input costs and economics
    input_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name=_('Input Cost')
    )
    
    market_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_('Market Price per kg')
    )
    
    # Additional data
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    data_source = models.CharField(max_length=100, blank=True, verbose_name=_('Data Source'))
    
    # Tracking
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_yields')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crop_management_yielddata'
        verbose_name = _('Yield Data')
        verbose_name_plural = _('Yield Data')
        unique_together = ['crop', 'variety', 'farm', 'harvest_year', 'harvest_season']
        ordering = ['-harvest_year', '-created_at']
    
    def __str__(self):
        return f"{str(self.crop.name)} - {str(self.farm.name)} ({self.harvest_year})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate yield per hectare
        if self.total_yield and self.area_cultivated:
            self.yield_per_hectare = self.total_yield / self.area_cultivated
        super().save(*args, **kwargs)


class FarmingPractice(models.Model):
    """Best farming practices and recommendations for crops"""
    
    PRACTICE_TYPES = [
        ('soil_preparation', _('Soil Preparation')),
        ('planting', _('Planting')),
        ('irrigation', _('Irrigation')),
        ('fertilization', _('Fertilization')),
        ('pest_control', _('Pest Control')),
        ('disease_management', _('Disease Management')),
        ('weed_control', _('Weed Control')),
        ('harvesting', _('Harvesting')),
        ('post_harvest', _('Post Harvest')),
        ('general', _('General')),
    ]
    
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='farming_practices')
    variety = models.ForeignKey(CropVariety, on_delete=models.CASCADE, null=True, blank=True, related_name='farming_practices')
    
    title = models.CharField(max_length=200, verbose_name=_('Practice Title'))
    practice_type = models.CharField(max_length=30, choices=PRACTICE_TYPES, verbose_name=_('Practice Type'))
    
    # Practice details
    description = models.TextField(verbose_name=_('Description'))
    implementation_steps = models.TextField(verbose_name=_('Implementation Steps'))
    
    # Timing and scheduling
    timing_description = models.TextField(blank=True, verbose_name=_('Timing Description'))
    days_after_planting = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_('Days after planting when this practice should be applied'),
        verbose_name=_('Days After Planting')
    )
    
    # Resources and requirements
    required_materials = models.TextField(blank=True, verbose_name=_('Required Materials'))
    estimated_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_('Estimated Cost')
    )
    
    labor_requirement = models.CharField(
        max_length=20,
        choices=[('low', _('Low')), ('medium', _('Medium')), ('high', _('High'))],
        default='medium',
        verbose_name=_('Labor Requirement')
    )
    
    # Effectiveness and impact
    expected_impact = models.TextField(blank=True, verbose_name=_('Expected Impact'))
    success_indicators = models.TextField(blank=True, verbose_name=_('Success Indicators'))
    
    # Regional applicability
    applicable_regions = models.TextField(blank=True, verbose_name=_('Applicable Regions'))
    climate_suitability = models.TextField(blank=True, verbose_name=_('Climate Suitability'))
    
    # Research and validation
    research_source = models.CharField(max_length=200, blank=True, verbose_name=_('Research Source'))
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('experimental', _('Experimental')),
            ('tested', _('Field Tested')),
            ('proven', _('Proven')),
            ('recommended', _('Recommended'))
        ],
        default='experimental',
        verbose_name=_('Validation Status')
    )
    
    # Priority and importance
    priority_level = models.CharField(
        max_length=10,
        choices=[('low', _('Low')), ('medium', _('Medium')), ('high', _('High')), ('critical', _('Critical'))],
        default='medium',
        verbose_name=_('Priority Level')
    )
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_practices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'crop_management_farmingpractice'
        verbose_name = _('Farming Practice')
        verbose_name_plural = _('Farming Practices')
        ordering = ['crop__name', 'practice_type', 'priority_level']
    
    def __str__(self):
        return f"{str(self.crop.name)} - {str(self.title)}"


class CropResearch(models.Model):
    """Research data and findings related to crops"""
    
    RESEARCH_TYPES = [
        ('yield_improvement', _('Yield Improvement')),
        ('disease_resistance', _('Disease Resistance')),
        ('pest_management', _('Pest Management')),
        ('quality_enhancement', _('Quality Enhancement')),
        ('climate_adaptation', _('Climate Adaptation')),
        ('nutrition_study', _('Nutrition Study')),
        ('market_analysis', _('Market Analysis')),
        ('sustainability', _('Sustainability')),
        ('other', _('Other')),
    ]
    
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='research_data')
    variety = models.ForeignKey(CropVariety, on_delete=models.CASCADE, null=True, blank=True, related_name='research_data')
    
    title = models.CharField(max_length=300, verbose_name=_('Research Title'))
    research_type = models.CharField(max_length=30, choices=RESEARCH_TYPES, verbose_name=_('Research Type'))
    
    # Research details
    objective = models.TextField(verbose_name=_('Research Objective'))
    methodology = models.TextField(verbose_name=_('Methodology'))
    findings = models.TextField(verbose_name=_('Key Findings'))
    conclusions = models.TextField(verbose_name=_('Conclusions'))
    
    # Research metadata
    research_institution = models.CharField(max_length=200, verbose_name=_('Research Institution'))
    principal_investigator = models.CharField(max_length=100, verbose_name=_('Principal Investigator'))
    research_period_start = models.DateField(verbose_name=_('Research Start Date'))
    research_period_end = models.DateField(null=True, blank=True, verbose_name=_('Research End Date'))
    
    # Publication and documentation
    publication_status = models.CharField(
        max_length=20,
        choices=[
            ('ongoing', _('Ongoing')),
            ('completed', _('Completed')),
            ('published', _('Published')),
            ('peer_reviewed', _('Peer Reviewed'))
        ],
        default='ongoing',
        verbose_name=_('Publication Status')
    )
    
    publication_reference = models.TextField(blank=True, verbose_name=_('Publication Reference'))
    doi = models.CharField(max_length=100, blank=True, verbose_name=_('DOI'))
    
    # Impact and applications
    practical_applications = models.TextField(blank=True, verbose_name=_('Practical Applications'))
    impact_assessment = models.TextField(blank=True, verbose_name=_('Impact Assessment'))
    
    # Files and attachments
    research_document = models.FileField(
        upload_to='crop_research/', null=True, blank=True,
        verbose_name=_('Research Document')
    )
    
    # Tracking
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_research')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'crop_management_cropresearch'
        verbose_name = _('Crop Research')
        verbose_name_plural = _('Crop Research')
        ordering = ['-research_period_start', '-created_at']
    
    def __str__(self):
        return f"{str(self.crop.name)} - {str(self.title)}"

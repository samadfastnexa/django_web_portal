import django_filters
from django.db.models import Q
from .models import Crop, CropVariety, YieldData, FarmingPractice, CropResearch


class CropFilter(django_filters.FilterSet):
    """Filter for Crop model"""
    
    name = django_filters.CharFilter(lookup_expr='icontains')
    scientific_name = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.ChoiceFilter(choices=Crop.CROP_CATEGORIES)
    growth_season = django_filters.ChoiceFilter(choices=Crop.GROWTH_SEASONS)
    water_requirement = django_filters.ChoiceFilter(
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    )
    growth_cycle_days_min = django_filters.NumberFilter(
        field_name='growth_cycle_days', lookup_expr='gte'
    )
    growth_cycle_days_max = django_filters.NumberFilter(
        field_name='growth_cycle_days', lookup_expr='lte'
    )
    created_after = django_filters.DateFilter(
        field_name='created_at', lookup_expr='gte'
    )
    created_before = django_filters.DateFilter(
        field_name='created_at', lookup_expr='lte'
    )
    
    class Meta:
        model = Crop
        fields = [
            'name', 'scientific_name', 'category', 'growth_season',
            'water_requirement', 'is_active'
        ]


class CropVarietyFilter(django_filters.FilterSet):
    """Filter for CropVariety model"""
    
    name = django_filters.CharFilter(lookup_expr='icontains')
    variety_code = django_filters.CharFilter(lookup_expr='icontains')
    crop = django_filters.ModelChoiceFilter(queryset=Crop.objects.filter(is_active=True))
    crop_name = django_filters.CharFilter(
        field_name='crop__name', lookup_expr='icontains'
    )
    crop_category = django_filters.ChoiceFilter(
        field_name='crop__category', choices=Crop.CROP_CATEGORIES
    )
    yield_potential_min = django_filters.NumberFilter(
        field_name='yield_potential', lookup_expr='gte'
    )
    yield_potential_max = django_filters.NumberFilter(
        field_name='yield_potential', lookup_expr='lte'
    )
    maturity_days_min = django_filters.NumberFilter(
        field_name='maturity_days', lookup_expr='gte'
    )
    maturity_days_max = django_filters.NumberFilter(
        field_name='maturity_days', lookup_expr='lte'
    )
    seed_availability = django_filters.ChoiceFilter(
        choices=[('available', 'Available'), ('limited', 'Limited'), ('unavailable', 'Unavailable')]
    )
    release_year_min = django_filters.NumberFilter(
        field_name='release_year', lookup_expr='gte'
    )
    release_year_max = django_filters.NumberFilter(
        field_name='release_year', lookup_expr='lte'
    )
    developed_by = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = CropVariety
        fields = [
            'name', 'variety_code', 'crop', 'seed_availability',
            'release_year', 'developed_by', 'is_active'
        ]


class YieldDataFilter(django_filters.FilterSet):
    """Filter for YieldData model"""
    
    crop = django_filters.ModelChoiceFilter(queryset=Crop.objects.filter(is_active=True))
    crop_name = django_filters.CharFilter(
        field_name='crop__name', lookup_expr='icontains'
    )
    crop_category = django_filters.ChoiceFilter(
        field_name='crop__category', choices=Crop.CROP_CATEGORIES
    )
    variety = django_filters.ModelChoiceFilter(
        queryset=CropVariety.objects.filter(is_active=True)
    )
    variety_name = django_filters.CharFilter(
        field_name='variety__name', lookup_expr='icontains'
    )
    farm_name = django_filters.CharFilter(
        field_name='farm__name', lookup_expr='icontains'
    )
    harvest_year = django_filters.NumberFilter()
    harvest_year_min = django_filters.NumberFilter(
        field_name='harvest_year', lookup_expr='gte'
    )
    harvest_year_max = django_filters.NumberFilter(
        field_name='harvest_year', lookup_expr='lte'
    )
    harvest_season = django_filters.ChoiceFilter(choices=Crop.GROWTH_SEASONS)
    
    # Yield filters
    yield_per_hectare_min = django_filters.NumberFilter(
        field_name='yield_per_hectare', lookup_expr='gte'
    )
    yield_per_hectare_max = django_filters.NumberFilter(
        field_name='yield_per_hectare', lookup_expr='lte'
    )
    total_yield_min = django_filters.NumberFilter(
        field_name='total_yield', lookup_expr='gte'
    )
    total_yield_max = django_filters.NumberFilter(
        field_name='total_yield', lookup_expr='lte'
    )
    area_cultivated_min = django_filters.NumberFilter(
        field_name='area_cultivated', lookup_expr='gte'
    )
    area_cultivated_max = django_filters.NumberFilter(
        field_name='area_cultivated', lookup_expr='lte'
    )
    
    # Quality and environmental filters
    quality_grade = django_filters.ChoiceFilter(
        choices=[('A', 'Grade A'), ('B', 'Grade B'), ('C', 'Grade C')]
    )
    rainfall_min = django_filters.NumberFilter(
        field_name='rainfall_mm', lookup_expr='gte'
    )
    rainfall_max = django_filters.NumberFilter(
        field_name='rainfall_mm', lookup_expr='lte'
    )
    temperature_min = django_filters.NumberFilter(
        field_name='temperature_avg', lookup_expr='gte'
    )
    temperature_max = django_filters.NumberFilter(
        field_name='temperature_avg', lookup_expr='lte'
    )
    
    # Economic filters
    input_cost_min = django_filters.NumberFilter(
        field_name='input_cost', lookup_expr='gte'
    )
    input_cost_max = django_filters.NumberFilter(
        field_name='input_cost', lookup_expr='lte'
    )
    market_price_min = django_filters.NumberFilter(
        field_name='market_price', lookup_expr='gte'
    )
    market_price_max = django_filters.NumberFilter(
        field_name='market_price', lookup_expr='lte'
    )
    
    # Date filters
    recorded_after = django_filters.DateFilter(
        field_name='created_at', lookup_expr='gte'
    )
    recorded_before = django_filters.DateFilter(
        field_name='created_at', lookup_expr='lte'
    )
    
    class Meta:
        model = YieldData
        fields = [
            'crop', 'variety', 'farm', 'harvest_year', 'harvest_season',
            'quality_grade'
        ]


class FarmingPracticeFilter(django_filters.FilterSet):
    """Filter for FarmingPractice model"""
    
    crop = django_filters.ModelChoiceFilter(queryset=Crop.objects.filter(is_active=True))
    crop_name = django_filters.CharFilter(
        field_name='crop__name', lookup_expr='icontains'
    )
    crop_category = django_filters.ChoiceFilter(
        field_name='crop__category', choices=Crop.CROP_CATEGORIES
    )
    variety = django_filters.ModelChoiceFilter(
        queryset=CropVariety.objects.filter(is_active=True)
    )
    title = django_filters.CharFilter(lookup_expr='icontains')
    practice_type = django_filters.ChoiceFilter(choices=FarmingPractice.PRACTICE_TYPES)
    validation_status = django_filters.ChoiceFilter(
        choices=[
            ('experimental', 'Experimental'),
            ('tested', 'Field Tested'),
            ('proven', 'Proven'),
            ('recommended', 'Recommended')
        ]
    )
    priority_level = django_filters.ChoiceFilter(
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]
    )
    labor_requirement = django_filters.ChoiceFilter(
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    )
    
    # Cost filters
    estimated_cost_min = django_filters.NumberFilter(
        field_name='estimated_cost', lookup_expr='gte'
    )
    estimated_cost_max = django_filters.NumberFilter(
        field_name='estimated_cost', lookup_expr='lte'
    )
    
    # Timing filters
    days_after_planting_min = django_filters.NumberFilter(
        field_name='days_after_planting', lookup_expr='gte'
    )
    days_after_planting_max = django_filters.NumberFilter(
        field_name='days_after_planting', lookup_expr='lte'
    )
    
    # Research source filter
    research_source = django_filters.CharFilter(lookup_expr='icontains')
    
    # Date filters
    created_after = django_filters.DateFilter(
        field_name='created_at', lookup_expr='gte'
    )
    created_before = django_filters.DateFilter(
        field_name='created_at', lookup_expr='lte'
    )
    
    class Meta:
        model = FarmingPractice
        fields = [
            'crop', 'variety', 'practice_type', 'validation_status',
            'priority_level', 'labor_requirement', 'is_active'
        ]


class CropResearchFilter(django_filters.FilterSet):
    """Filter for CropResearch model"""
    
    crop = django_filters.ModelChoiceFilter(queryset=Crop.objects.filter(is_active=True))
    crop_name = django_filters.CharFilter(
        field_name='crop__name', lookup_expr='icontains'
    )
    crop_category = django_filters.ChoiceFilter(
        field_name='crop__category', choices=Crop.CROP_CATEGORIES
    )
    variety = django_filters.ModelChoiceFilter(
        queryset=CropVariety.objects.filter(is_active=True)
    )
    title = django_filters.CharFilter(lookup_expr='icontains')
    research_type = django_filters.ChoiceFilter(choices=CropResearch.RESEARCH_TYPES)
    research_institution = django_filters.CharFilter(lookup_expr='icontains')
    principal_investigator = django_filters.CharFilter(lookup_expr='icontains')
    publication_status = django_filters.ChoiceFilter(
        choices=[
            ('ongoing', 'Ongoing'),
            ('completed', 'Completed'),
            ('published', 'Published'),
            ('peer_reviewed', 'Peer Reviewed')
        ]
    )
    
    # Date filters
    research_start_after = django_filters.DateFilter(
        field_name='research_period_start', lookup_expr='gte'
    )
    research_start_before = django_filters.DateFilter(
        field_name='research_period_start', lookup_expr='lte'
    )
    research_end_after = django_filters.DateFilter(
        field_name='research_period_end', lookup_expr='gte'
    )
    research_end_before = django_filters.DateFilter(
        field_name='research_period_end', lookup_expr='lte'
    )
    
    # Year filters for easier searching
    research_year = django_filters.NumberFilter(
        field_name='research_period_start__year'
    )
    
    # DOI filter
    has_doi = django_filters.BooleanFilter(
        field_name='doi', lookup_expr='isnull', exclude=True
    )
    
    # Document filter
    has_document = django_filters.BooleanFilter(
        field_name='research_document', lookup_expr='isnull', exclude=True
    )
    
    # Created date filters
    added_after = django_filters.DateFilter(
        field_name='created_at', lookup_expr='gte'
    )
    added_before = django_filters.DateFilter(
        field_name='created_at', lookup_expr='lte'
    )
    
    class Meta:
        model = CropResearch
        fields = [
            'crop', 'variety', 'research_type', 'research_institution',
            'principal_investigator', 'publication_status', 'research_year',
            'is_active'
        ]


# Custom filter for advanced search across multiple fields
class CropAdvancedFilter(django_filters.FilterSet):
    """Advanced filter for comprehensive crop search"""
    
    search = django_filters.CharFilter(method='filter_search')
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        if value:
            return queryset.filter(
                Q(name__icontains=value) |
                Q(scientific_name__icontains=value) |
                Q(description__icontains=value) |
                Q(varieties__name__icontains=value) |
                Q(varieties__description__icontains=value)
            ).distinct()
        return queryset
    
    class Meta:
        model = Crop
        fields = ['search']


class YieldAnalyticsFilter(django_filters.FilterSet):
    """Filter for yield analytics and reporting"""
    
    crop_category = django_filters.ChoiceFilter(
        field_name='crop__category', choices=Crop.CROP_CATEGORIES
    )
    growth_season = django_filters.ChoiceFilter(
        field_name='crop__growth_season', choices=Crop.GROWTH_SEASONS
    )
    year_range_start = django_filters.NumberFilter(
        field_name='harvest_year', lookup_expr='gte'
    )
    year_range_end = django_filters.NumberFilter(
        field_name='harvest_year', lookup_expr='lte'
    )
    region = django_filters.CharFilter(
        field_name='farm__location', lookup_expr='icontains'
    )
    
    class Meta:
        model = YieldData
        fields = ['crop_category', 'growth_season', 'region']
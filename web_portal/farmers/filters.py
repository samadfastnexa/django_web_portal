import django_filters
from django.db.models import Q
from .models import Farmer, FarmingHistory


class FarmerFilter(django_filters.FilterSet):
    """Filter class for Farmer model with comprehensive search and filtering options"""
    
    # Text search across multiple fields
    search = django_filters.CharFilter(method='filter_search', label='Search')
    
    # Personal information filters
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    farmer_id = django_filters.CharFilter(lookup_expr='icontains')
    gender = django_filters.ChoiceFilter(choices=Farmer.GENDER_CHOICES)
    
    # Location filters
    village = django_filters.CharFilter(lookup_expr='icontains')
    tehsil = django_filters.CharFilter(lookup_expr='icontains')
    district = django_filters.CharFilter(lookup_expr='icontains')
    province = django_filters.CharFilter(lookup_expr='icontains')
    
    # Contact filters
    primary_phone = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    
    # Farm information filters
    total_land_area_min = django_filters.NumberFilter(field_name='total_land_area', lookup_expr='gte')
    total_land_area_max = django_filters.NumberFilter(field_name='total_land_area', lookup_expr='lte')
    
    education_level = django_filters.ChoiceFilter(choices=Farmer.EDUCATION_CHOICES)
    

    
    # Date filters
    registration_date_from = django_filters.DateFilter(field_name='registration_date', lookup_expr='gte')
    registration_date_to = django_filters.DateFilter(field_name='registration_date', lookup_expr='lte')
    
    # Age range filter (calculated field)
    age_min = django_filters.NumberFilter(method='filter_age_min')
    age_max = django_filters.NumberFilter(method='filter_age_max')
    
    class Meta:
        model = Farmer
        fields = {
            'farmer_id': ['exact', 'icontains'],
            'first_name': ['exact', 'icontains'],
            'last_name': ['exact', 'icontains'],
            'village': ['exact', 'icontains'],
            'district': ['exact', 'icontains'],
            'province': ['exact', 'icontains'],
            'gender': ['exact'],
            'education_level': ['exact'],

            'registration_date': ['exact', 'gte', 'lte'],
        }
    
    def filter_search(self, queryset, name, value):
        """Global search across multiple fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(farmer_id__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(father_name__icontains=value) |
            Q(primary_phone__icontains=value) |
            Q(email__icontains=value) |
            Q(village__icontains=value) |
            Q(tehsil__icontains=value) |
            Q(district__icontains=value) |
            Q(province__icontains=value) |
            Q(national_id__icontains=value)
        )
    
    def filter_age_min(self, queryset, name, value):
        """Filter by minimum age"""
        if not value:
            return queryset
        
        from django.utils import timezone
        from datetime import date
        
        # Calculate the maximum birth date for the minimum age
        today = date.today()
        max_birth_date = date(today.year - value, today.month, today.day)
        
        return queryset.filter(date_of_birth__lte=max_birth_date)
    
    def filter_age_max(self, queryset, name, value):
        """Filter by maximum age"""
        if not value:
            return queryset
        
        from django.utils import timezone
        from datetime import date
        
        # Calculate the minimum birth date for the maximum age
        today = date.today()
        min_birth_date = date(today.year - value - 1, today.month, today.day)
        
        return queryset.filter(date_of_birth__gte=min_birth_date)


class FarmingHistoryFilter(django_filters.FilterSet):
    """Filter class for FarmingHistory model"""
    
    # Basic filters
    farmer = django_filters.ModelChoiceFilter(queryset=Farmer.objects.all())
    year = django_filters.NumberFilter()
    season = django_filters.ChoiceFilter(choices=FarmingHistory.SEASON_CHOICES)
    crop_name = django_filters.CharFilter(lookup_expr='icontains')
    
    # Range filters
    year_from = django_filters.NumberFilter(field_name='year', lookup_expr='gte')
    year_to = django_filters.NumberFilter(field_name='year', lookup_expr='lte')
    
    area_cultivated_min = django_filters.NumberFilter(field_name='area_cultivated', lookup_expr='gte')
    area_cultivated_max = django_filters.NumberFilter(field_name='area_cultivated', lookup_expr='lte')
    
    total_yield_min = django_filters.NumberFilter(field_name='total_yield', lookup_expr='gte')
    total_yield_max = django_filters.NumberFilter(field_name='total_yield', lookup_expr='lte')
    
    yield_per_acre_min = django_filters.NumberFilter(field_name='yield_per_acre', lookup_expr='gte')
    yield_per_acre_max = django_filters.NumberFilter(field_name='yield_per_acre', lookup_expr='lte')
    
    input_cost_min = django_filters.NumberFilter(field_name='input_cost', lookup_expr='gte')
    input_cost_max = django_filters.NumberFilter(field_name='input_cost', lookup_expr='lte')
    
    total_income_min = django_filters.NumberFilter(field_name='total_income', lookup_expr='gte')
    total_income_max = django_filters.NumberFilter(field_name='total_income', lookup_expr='lte')
    
    profit_loss_min = django_filters.NumberFilter(field_name='profit_loss', lookup_expr='gte')
    profit_loss_max = django_filters.NumberFilter(field_name='profit_loss', lookup_expr='lte')
    
    # Text search
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = FarmingHistory
        fields = {
            'year': ['exact', 'gte', 'lte'],
            'season': ['exact'],
            'crop_name': ['exact', 'icontains'],
            'area_cultivated': ['exact', 'gte', 'lte'],
            'total_yield': ['exact', 'gte', 'lte'],
            'yield_per_acre': ['exact', 'gte', 'lte'],
            'input_cost': ['exact', 'gte', 'lte'],
            'total_income': ['exact', 'gte', 'lte'],
            'profit_loss': ['exact', 'gte', 'lte'],
        }
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(crop_name__icontains=value) |
            Q(farming_practices_used__icontains=value) |
            Q(challenges_faced__icontains=value) |
            Q(notes__icontains=value) |
            Q(farmer__first_name__icontains=value) |
            Q(farmer__last_name__icontains=value) |
            Q(farmer__farmer_id__icontains=value)
        )
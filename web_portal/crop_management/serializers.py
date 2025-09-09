from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Crop, CropVariety, YieldData, FarmingPractice, CropResearch
from farm.models import Farm

User = get_user_model()


class CropSerializer(serializers.ModelSerializer):
    """Serializer for Crop model"""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    growth_season_display = serializers.CharField(source='get_growth_season_display', read_only=True)
    water_requirement_display = serializers.CharField(source='get_water_requirement_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    varieties_count = serializers.SerializerMethodField()
    yield_records_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Crop
        fields = [
            'id', 'name', 'scientific_name', 'category', 'category_display',
            'growth_season', 'growth_season_display', 'growth_cycle_days',
            'market_availability', 'economic_importance', 'water_requirement',
            'water_requirement_display', 'soil_type_preference', 'climate_requirement',
            'description', 'nutritional_value', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'is_active', 'varieties_count', 'yield_records_count'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_varieties_count(self, obj):
        return obj.varieties.filter(is_active=True).count()
    
    def get_yield_records_count(self, obj):
        return obj.yield_records.count()
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CropVarietySerializer(serializers.ModelSerializer):
    """Serializer for CropVariety model"""
    
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    seed_availability_display = serializers.CharField(source='get_seed_availability_display', read_only=True)
    yield_records_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CropVariety
        fields = [
            'id', 'crop', 'crop_name', 'name', 'variety_code', 'yield_potential',
            'maturity_days', 'disease_resistance', 'pest_resistance',
            'quality_attributes', 'special_requirements', 'recommended_regions',
            'seed_availability', 'seed_availability_display', 'description',
            'developed_by', 'release_year', 'created_at', 'updated_at',
            'is_active', 'yield_records_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_yield_records_count(self, obj):
        return obj.yield_records.count()


class YieldDataSerializer(serializers.ModelSerializer):
    """Serializer for YieldData model"""
    
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    variety_name = serializers.CharField(source='variety.name', read_only=True)
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    harvest_season_display = serializers.CharField(source='get_harvest_season_display', read_only=True)
    quality_grade_display = serializers.CharField(source='get_quality_grade_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    profit_per_hectare = serializers.SerializerMethodField()
    
    class Meta:
        model = YieldData
        fields = [
            'id', 'crop', 'crop_name', 'variety', 'variety_name', 'farm', 'farm_name',
            'harvest_year', 'harvest_season', 'harvest_season_display',
            'area_cultivated', 'total_yield', 'yield_per_hectare',
            'quality_grade', 'quality_grade_display', 'rainfall_mm',
            'temperature_avg', 'input_cost', 'market_price', 'profit_per_hectare',
            'notes', 'data_source', 'recorded_by', 'recorded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['yield_per_hectare', 'recorded_by', 'created_at', 'updated_at']
    
    def get_profit_per_hectare(self, obj):
        if obj.market_price and obj.input_cost and obj.yield_per_hectare:
            revenue = obj.yield_per_hectare * obj.market_price
            cost_per_hectare = obj.input_cost / obj.area_cultivated if obj.area_cultivated else 0
            return revenue - cost_per_hectare
        return None
    
    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)


class FarmingPracticeSerializer(serializers.ModelSerializer):
    """Serializer for FarmingPractice model"""
    
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    variety_name = serializers.CharField(source='variety.name', read_only=True)
    practice_type_display = serializers.CharField(source='get_practice_type_display', read_only=True)
    labor_requirement_display = serializers.CharField(source='get_labor_requirement_display', read_only=True)
    validation_status_display = serializers.CharField(source='get_validation_status_display', read_only=True)
    priority_level_display = serializers.CharField(source='get_priority_level_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = FarmingPractice
        fields = [
            'id', 'crop', 'crop_name', 'variety', 'variety_name', 'title',
            'practice_type', 'practice_type_display', 'description',
            'implementation_steps', 'timing_description', 'days_after_planting',
            'required_materials', 'estimated_cost', 'labor_requirement',
            'labor_requirement_display', 'expected_impact', 'success_indicators',
            'applicable_regions', 'climate_suitability', 'research_source',
            'validation_status', 'validation_status_display', 'priority_level',
            'priority_level_display', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CropResearchSerializer(serializers.ModelSerializer):
    """Serializer for CropResearch model"""
    
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    variety_name = serializers.CharField(source='variety.name', read_only=True)
    research_type_display = serializers.CharField(source='get_research_type_display', read_only=True)
    publication_status_display = serializers.CharField(source='get_publication_status_display', read_only=True)
    added_by_name = serializers.CharField(source='added_by.get_full_name', read_only=True)
    research_duration_days = serializers.SerializerMethodField()
    
    class Meta:
        model = CropResearch
        fields = [
            'id', 'crop', 'crop_name', 'variety', 'variety_name', 'title',
            'research_type', 'research_type_display', 'objective', 'methodology',
            'findings', 'conclusions', 'research_institution', 'principal_investigator',
            'research_period_start', 'research_period_end', 'research_duration_days',
            'publication_status', 'publication_status_display', 'publication_reference',
            'doi', 'practical_applications', 'impact_assessment', 'research_document',
            'added_by', 'added_by_name', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['added_by', 'created_at', 'updated_at']
    
    def get_research_duration_days(self, obj):
        if obj.research_period_start and obj.research_period_end:
            return (obj.research_period_end - obj.research_period_start).days
        return None
    
    def create(self, validated_data):
        validated_data['added_by'] = self.context['request'].user
        return super().create(validated_data)


# Nested serializers for detailed views
class CropDetailSerializer(CropSerializer):
    """Detailed serializer for Crop with related data"""
    
    varieties = CropVarietySerializer(many=True, read_only=True)
    recent_yield_data = serializers.SerializerMethodField()
    farming_practices = serializers.SerializerMethodField()
    research_data = serializers.SerializerMethodField()
    
    class Meta(CropSerializer.Meta):
        fields = CropSerializer.Meta.fields + [
            'varieties', 'recent_yield_data', 'farming_practices', 'research_data'
        ]
    
    def get_recent_yield_data(self, obj):
        recent_yields = obj.yield_records.order_by('-harvest_year', '-created_at')[:5]
        return YieldDataSerializer(recent_yields, many=True, context=self.context).data
    
    def get_farming_practices(self, obj):
        practices = obj.farming_practices.filter(is_active=True).order_by('practice_type', 'priority_level')[:10]
        return FarmingPracticeSerializer(practices, many=True, context=self.context).data
    
    def get_research_data(self, obj):
        research = obj.research_data.filter(is_active=True).order_by('-research_period_start')[:5]
        return CropResearchSerializer(research, many=True, context=self.context).data


class CropVarietyDetailSerializer(CropVarietySerializer):
    """Detailed serializer for CropVariety with related data"""
    
    crop = CropSerializer(read_only=True)
    yield_data = serializers.SerializerMethodField()
    farming_practices = serializers.SerializerMethodField()
    research_data = serializers.SerializerMethodField()
    
    class Meta(CropVarietySerializer.Meta):
        fields = CropVarietySerializer.Meta.fields + [
            'yield_data', 'farming_practices', 'research_data'
        ]
    
    def get_yield_data(self, obj):
        yields = obj.yield_records.order_by('-harvest_year', '-created_at')[:10]
        return YieldDataSerializer(yields, many=True, context=self.context).data
    
    def get_farming_practices(self, obj):
        practices = obj.farming_practices.filter(is_active=True).order_by('practice_type', 'priority_level')
        return FarmingPracticeSerializer(practices, many=True, context=self.context).data
    
    def get_research_data(self, obj):
        research = obj.research_data.filter(is_active=True).order_by('-research_period_start')
        return CropResearchSerializer(research, many=True, context=self.context).data


# Summary serializers for analytics
class CropSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for crop analytics"""
    
    total_varieties = serializers.SerializerMethodField()
    total_yield_records = serializers.SerializerMethodField()
    average_yield = serializers.SerializerMethodField()
    total_area_cultivated = serializers.SerializerMethodField()
    
    class Meta:
        model = Crop
        fields = [
            'id', 'name', 'category', 'growth_season', 'total_varieties',
            'total_yield_records', 'average_yield', 'total_area_cultivated'
        ]
    
    def get_total_varieties(self, obj):
        return obj.varieties.filter(is_active=True).count()
    
    def get_total_yield_records(self, obj):
        return obj.yield_records.count()
    
    def get_average_yield(self, obj):
        yields = obj.yield_records.values_list('yield_per_hectare', flat=True)
        if yields:
            return sum(yields) / len(yields)
        return 0
    
    def get_total_area_cultivated(self, obj):
        areas = obj.yield_records.values_list('area_cultivated', flat=True)
        return sum(areas) if areas else 0


class YieldAnalyticsSerializer(serializers.Serializer):
    """Serializer for yield analytics data"""
    
    crop_id = serializers.IntegerField()
    crop_name = serializers.CharField()
    year = serializers.IntegerField()
    season = serializers.CharField()
    total_area = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_yield = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_yield_per_hectare = serializers.DecimalField(max_digits=10, decimal_places=2)
    farm_count = serializers.IntegerField()
    average_quality_grade = serializers.CharField()
    total_input_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_market_price = serializers.DecimalField(max_digits=10, decimal_places=2)
from rest_framework import serializers
from .models import Farmer, FarmingHistory


class FarmingHistorySerializer(serializers.ModelSerializer):
    """Serializer for FarmingHistory model"""
    
    class Meta:
        model = FarmingHistory
        fields = [
            'id', 'year', 'season', 'crop_name', 'area_cultivated',
            'total_yield', 'yield_per_acre', 'input_cost', 'market_price',
            'total_income', 'profit_loss', 'farming_practices_used',
            'challenges_faced', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class FarmerListSerializer(serializers.ModelSerializer):
    """Simplified serializer for farmer list view"""
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = Farmer
        fields = [
            'id', 'farmer_id', 'first_name', 'last_name', 'full_name',
            'primary_phone', 'village', 'district', 'total_land_area',
            'main_crops_grown', 'farming_experience', 'is_active',
            'is_verified', 'registration_date', 'age'
        ]


class FarmerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for farmer detail view"""
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    farming_history = FarmingHistorySerializer(many=True, read_only=True)
    registered_by_name = serializers.CharField(source='registered_by.get_full_name', read_only=True)
    
    class Meta:
        model = Farmer
        fields = [
            'id', 'farmer_id', 'first_name', 'last_name', 'full_name', 'name',
            'father_name', 'date_of_birth', 'age', 'gender', 'national_id',
            'primary_phone', 'secondary_phone', 'email',
            'address', 'village', 'tehsil', 'district', 'province', 'postal_code',
            'current_latitude', 'current_longitude', 'farm_latitude', 'farm_longitude',
            'education_level', 'occupation_besides_farming',
            'total_land_area', 'cultivated_area', 'farm_ownership_type', 'land_documents',
            'farming_experience', 'years_of_farming', 'main_crops_grown',
            'farming_methods', 'irrigation_source',
            'annual_income_range', 'bank_account_details',
            'family_members_count', 'dependents_count', 'family_involved_in_farming',
            'registration_date', 'last_updated', 'is_active', 'is_verified',
            'registered_by', 'registered_by_name', 'notes', 'profile_picture',
            'farming_history'
        ]
        read_only_fields = ['registration_date', 'last_updated', 'full_name', 'age', 'name']


class FarmerCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating farmers"""
    
    class Meta:
        model = Farmer
        fields = [
            'farmer_id', 'first_name', 'last_name', 'father_name',
            'date_of_birth', 'gender', 'national_id',
            'primary_phone', 'secondary_phone', 'email',
            'address', 'village', 'tehsil', 'district', 'province', 'postal_code',
            'current_latitude', 'current_longitude', 'farm_latitude', 'farm_longitude',
            'education_level', 'occupation_besides_farming',
            'total_land_area', 'cultivated_area', 'farm_ownership_type', 'land_documents',
            'farming_experience', 'years_of_farming', 'main_crops_grown',
            'farming_methods', 'irrigation_source',
            'annual_income_range', 'bank_account_details',
            'family_members_count', 'dependents_count', 'family_involved_in_farming',
            'is_active', 'is_verified', 'notes', 'profile_picture'
        ]
    
    def validate_farmer_id(self, value):
        """Validate farmer ID uniqueness"""
        if self.instance:
            # For updates, exclude current instance
            if Farmer.objects.exclude(pk=self.instance.pk).filter(farmer_id=value).exists():
                raise serializers.ValidationError("Farmer ID already exists.")
        else:
            # For creation
            if Farmer.objects.filter(farmer_id=value).exists():
                raise serializers.ValidationError("Farmer ID already exists.")
        return value
    
    def validate_national_id(self, value):
        """Validate national ID uniqueness"""
        if value:  # Only validate if value is provided
            if self.instance:
                # For updates, exclude current instance
                if Farmer.objects.exclude(pk=self.instance.pk).filter(national_id=value).exists():
                    raise serializers.ValidationError("National ID already exists.")
            else:
                # For creation
                if Farmer.objects.filter(national_id=value).exists():
                    raise serializers.ValidationError("National ID already exists.")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Validate that cultivated area doesn't exceed total land area
        total_area = data.get('total_land_area')
        cultivated_area = data.get('cultivated_area')
        
        if total_area and cultivated_area and cultivated_area > total_area:
            raise serializers.ValidationError({
                'cultivated_area': 'Cultivated area cannot exceed total land area.'
            })
        
        return data


# Backward compatibility - keep the original FarmerSerializer
class FarmerSerializer(FarmerDetailSerializer):
    """Main farmer serializer - inherits from detailed serializer for backward compatibility"""
    pass

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
            'education_level', 'registration_date', 'age', 'profile_picture',
            'current_crops_and_acreage', 'crop_calendar'
        ]


class FarmerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for farmer detail view"""
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    registered_by_name = serializers.CharField(source='registered_by.get_full_name', read_only=True)
    
    class Meta:
        model = Farmer
        fields = [
            'id', 'farmer_id', 'first_name', 'last_name', 'full_name', 'name',
            'father_name', 'date_of_birth', 'age', 'gender', 'cnic',
            'primary_phone', 'secondary_phone', 'email',
            'address', 'village', 'tehsil', 'district', 'province',
            'education_level', 'total_land_area',
            'current_crops_and_acreage', 'crop_calendar',
            'registration_date', 'last_updated',
            'registered_by', 'registered_by_name', 'notes', 'profile_picture'
        ]
        read_only_fields = ['registration_date', 'last_updated', 'full_name', 'age', 'name']


class FarmerCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating farmers"""
    farmer_id = serializers.CharField(required=False, allow_blank=True, help_text="Leave blank for auto-generation")
    
    class Meta:
        model = Farmer
        fields = [
            'farmer_id', 'first_name', 'last_name', 'father_name',
            'date_of_birth', 'gender', 'cnic',
            'primary_phone', 'secondary_phone', 'email',
            'address', 'village', 'tehsil', 'district', 'province',
            'education_level', 'total_land_area',
            'current_crops_and_acreage', 'crop_calendar',
            'notes', 'profile_picture'
        ]
        read_only_fields = ['id', 'registration_date', 'last_updated']
    
    def validate_farmer_id(self, value):
        """Validate farmer ID uniqueness"""
        # If value is empty or None, it will be auto-generated, so no validation needed
        if not value:
            return value
            
        if self.instance:
            # For updates, exclude current instance
            if Farmer.objects.exclude(pk=self.instance.pk).filter(farmer_id=value).exists():
                raise serializers.ValidationError("Farmer ID already exists.")
        else:
            # For creation
            if Farmer.objects.filter(farmer_id=value).exists():
                raise serializers.ValidationError("Farmer ID already exists.")
        return value
    
    def validate_cnic(self, value):
        """Validate CNIC uniqueness"""
        if value:  # Only validate if value is provided
            if self.instance:
                # For updates, exclude current instance
                if Farmer.objects.exclude(pk=self.instance.pk).filter(cnic=value).exists():
                    raise serializers.ValidationError("CNIC already exists.")
            else:
                # For creation
                if Farmer.objects.filter(cnic=value).exists():
                    raise serializers.ValidationError("CNIC already exists.")
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

# farm/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Farm

User = get_user_model()

class FarmCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new farms"""
    
    class Meta:
        model = Farm
        fields = [
            "name", "owner", "address", "geolocation", 
            "size", "soil_type", "ownership_details", "is_active"
        ]
        extra_kwargs = {
            'name': {
                'help_text': 'Name of the farm (max 200 characters)',
                'required': True
            },
            'owner': {
                'help_text': 'Owner of the farm (User ID)',
                'required': True
            },
            'address': {
                'help_text': 'Physical address of the farm',
                'required': True
            },
            'geolocation': {
                'help_text': 'Geographic coordinates (latitude,longitude)',
                'required': True
            },
            'size': {
                'help_text': 'Size of the farm in acres/hectares',
                'required': True
            },
            'soil_type': {
                'help_text': 'Type of soil (clay, sandy, silty, peaty, chalky, loamy)',
                'required': True
            },
            'ownership_details': {
                'help_text': 'Additional ownership information (optional)',
                'required': False
            },
            'is_active': {
                'help_text': 'Whether the farm is currently active',
                'required': False,
                'default': True
            }
        }

    def validate_size(self, value):
        """Validate farm size"""
        if value <= 0:
            raise serializers.ValidationError("Farm size must be greater than 0")
        if value > 999999.99:
            raise serializers.ValidationError("Farm size cannot exceed 999,999.99 acres/hectares")
        return value

    def validate_name(self, value):
        """Validate farm name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Farm name must be at least 2 characters long")
        return value.strip()

class FarmUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing farms"""
    
    class Meta:
        model = Farm
        fields = [
            "name", "address", "geolocation", "size", 
            "soil_type", "ownership_details", "is_active"
        ]
        extra_kwargs = {
            'name': {'help_text': 'Name of the farm (max 200 characters)'},
            'address': {'help_text': 'Physical address of the farm'},
            'geolocation': {'help_text': 'Geographic coordinates (latitude,longitude)'},
            'size': {'help_text': 'Size of the farm in acres/hectares'},
            'soil_type': {'help_text': 'Type of soil (clay, sandy, silty, peaty, chalky, loamy)'},
            'ownership_details': {'help_text': 'Additional ownership information (optional)'},
            'is_active': {'help_text': 'Whether the farm is currently active'}
        }

    def validate_size(self, value):
        """Validate farm size"""
        if value <= 0:
            raise serializers.ValidationError("Farm size must be greater than 0")
        if value > 999999.99:
            raise serializers.ValidationError("Farm size cannot exceed 999,999.99 acres/hectares")
        return value

class FarmSerializer(serializers.ModelSerializer):
    """Main serializer for farm data with all fields including read-only ones"""
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    owner_email = serializers.CharField(source="owner.email", read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Farm
        fields = [
            "id", "name", "owner", "owner_name", "owner_email",
            "address", "geolocation", "size", "soil_type",
            "ownership_details", "is_active", "status_display",
            "created_at", "updated_at", "deleted_at"
        ]
        read_only_fields = ["id", "owner_name", "owner_email", "status_display", "created_at", "updated_at", "deleted_at"]
        extra_kwargs = {
            'name': {'help_text': 'Name of the farm'},
            'owner': {'help_text': 'Owner of the farm'},
            'address': {'help_text': 'Physical address of the farm'},
            'geolocation': {'help_text': 'Geographic coordinates'},
            'size': {'help_text': 'Size in acres/hectares'},
            'soil_type': {'help_text': 'Type of soil'},
            'ownership_details': {'help_text': 'Additional ownership information'},
            'is_active': {'help_text': 'Whether the farm is currently active'},
            'created_at': {'help_text': 'Date and time when farm was created'},
            'updated_at': {'help_text': 'Date and time when farm was last updated'},
            'deleted_at': {'help_text': 'Date and time when farm was soft deleted (null if not deleted)'}
        }

    def get_status_display(self, obj):
        """Get human-readable status"""
        if obj.deleted_at:
            return "Deleted"
        elif obj.is_active:
            return "Active"
        else:
            return "Inactive"

class FarmListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for farm listings"""
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Farm
        fields = [
            "id", "name", "owner_name", "size", "soil_type",
            "is_active", "status_display", "created_at"
        ]
        read_only_fields = ["id", "owner_name", "status_display", "created_at"]

    def get_status_display(self, obj):
        """Get human-readable status"""
        if obj.deleted_at:
            return "Deleted"
        elif obj.is_active:
            return "Active"
        else:
            return "Inactive"

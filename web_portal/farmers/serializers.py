from rest_framework import serializers
from .models import Farmer

class FarmerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        help_text="Full name of the farmer",
        style={'placeholder': 'John Smith'}
    )
    current_latitude = serializers.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        required=False, 
        allow_null=True,
        help_text="Current GPS latitude coordinate",
        style={'placeholder': '31.520370'}
    )
    current_longitude = serializers.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        required=False, 
        allow_null=True,
        help_text="Current GPS longitude coordinate",
        style={'placeholder': '74.358749'}
    )
    farm_latitude = serializers.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        required=False, 
        allow_null=True,
        help_text="Farm location GPS latitude coordinate",
        style={'placeholder': '31.521000'}
    )
    farm_longitude = serializers.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        required=False, 
        allow_null=True,
        help_text="Farm location GPS longitude coordinate",
        style={'placeholder': '74.359000'}
    )

    class Meta:
        model = Farmer
        fields = ['id', 'name', 'current_latitude', 'current_longitude', 'farm_latitude', 'farm_longitude']

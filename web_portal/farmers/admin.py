from django.contrib import admin
from .models import Farmer
from django_google_maps.widgets import GoogleMapsAddressWidget
from django import forms

class FarmerAdminForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = '__all__'
        widgets = {
            'farm_address': GoogleMapsAddressWidget,
        }

class FarmerAdmin(admin.ModelAdmin):
    form = FarmerAdminForm

admin.site.register(Farmer, FarmerAdmin)

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Crop, CropVariety, YieldData, FarmingPractice, CropResearch


# Custom admin site configuration
admin.site.site_header = "Tarzan Admin Panel by Fastnexa"
admin.site.site_title = "Tarzan Management Admin"
admin.site.index_title = "Welcome to Tarzan by Fastnexa"

# preferences/admin.py

from django.contrib import admin
from .models import UserSetting

@admin.register(UserSetting)
class UserSettingAdmin(admin.ModelAdmin):
    list_display = ['slug', 'user', 'color_theme', 'dark_mode', 'language', 'company_timings']

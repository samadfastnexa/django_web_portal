from django.contrib import admin
from .models import UserSetting

@admin.register(UserSetting)
class UserSettingAdmin(admin.ModelAdmin):
    list_display = ['slug', 'user', 'type', 'color_theme', 'dark_mode', 'language', 'radius_km']
    list_filter = ['user', 'language', 'dark_mode']
    search_fields = ['slug', 'user__username', 'language']
    ordering = ['slug']

    def type(self, obj):
        return 'global' if obj.user is None else 'user'
    type.short_description = 'Setting Type'

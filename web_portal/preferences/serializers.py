from rest_framework import serializers
from .models import Setting

class SettingSerializer(serializers.ModelSerializer):
    value = serializers.JSONField()  # ✅ Accepts dict, list, int, etc.
    class Meta:
        model = Setting
        fields = ['id', 'user', 'slug', 'value']
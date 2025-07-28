from rest_framework import serializers
from .models import UserSetting

class UserSettingSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = UserSetting
        fields = [
            'id',
            'user',
            'slug',
            'color_theme',
            'dark_mode',
            'language',
            'company_timings',
            'value',
            'radius_km',
            'type'
        ]
        read_only_fields = ['user']  # user is auto-set in the view

    def validate_slug(self, value):
        request = self.context.get('request')
        user = request.user if request else None
        is_global = request and request.data.get('user') in [None, '', 'null']

        if is_global:
            if UserSetting.objects.filter(user__isnull=True, slug=value).exists():
                raise serializers.ValidationError("A global setting with this slug already exists.")
        else:
            if UserSetting.objects.filter(user=user, slug=value).exists():
                raise serializers.ValidationError("You already have a setting with this slug.")
        return value

    def get_type(self, obj):
        return 'global' if obj.user is None else 'user'

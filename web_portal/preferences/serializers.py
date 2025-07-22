from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import UserSetting

class UserSettingSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(
        validators=[UniqueValidator(queryset=UserSetting.objects.all())]
    )

    class Meta:
        model = UserSetting
        fields = '__all__'

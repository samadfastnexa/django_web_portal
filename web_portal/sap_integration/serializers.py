from rest_framework import serializers
from .models import Policy


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = (
            'id', 'code', 'name', 'policy', 'valid_from', 'valid_to', 'active',
            'created_at', 'updated_at'
        )
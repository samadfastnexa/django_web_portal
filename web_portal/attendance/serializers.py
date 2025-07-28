from rest_framework import serializers
from .models import Attendance, AttendanceRequest

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ['check_in_gap', 'check_out_gap', 'created_at']

class AttendanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRequest
        fields = '__all__'
        read_only_fields = [
            'status', 'created_at', 'updated_at',
            'check_in_gap', 'check_out_gap', 'user'
        ]

    # ✅ Remove this method completely, let view pass `user`
    # def create(self, validated_data):
    #     validated_data['user'] = self.context['request'].user
    #     return AttendanceRequest.objects.create(**validated_data)

from rest_framework import serializers
from .models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    check_in_gap = serializers.DurationField(read_only=True)
    check_out_gap = serializers.DurationField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'
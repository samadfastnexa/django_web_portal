from rest_framework import serializers
from .models import Attendance, AttendanceRequest

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ['check_in_gap', 'check_out_gap', 'created_at','source', 'user']

    def create(self, validated_data):
        request = self.context['request']
        validated_data['user'] = request.user
        return super().create(validated_data)

        
class AttendanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRequest
        fields = '__all__'
        read_only_fields = [
            'user', 'status', 'check_in_gap',
            'check_out_gap', 'created_at', 'updated_at'
        ]
        
    def create(self, validated_data):
        # 👤 Set the user from the request context (ignore input from client)
        user = self.context['request'].user
        validated_data['user'] = user

        # 🧾 Extract required fields
        check_type = validated_data.get('check_type')
        check_in_time = validated_data.get('check_in_time')
        check_out_time = validated_data.get('check_out_time')

        # 📅 Determine the target date from check-in or check-out time
        target_date = None
        if check_type == 'check_in' and check_in_time:
            target_date = check_in_time.date()
        elif check_type == 'check_out' and check_out_time:
            target_date = check_out_time.date()

        # 🔍 Check if an attendance already exists for this user on that date
        attendance = Attendance.objects.filter(
            attendee=user,
            check_in_time__date=target_date
        ).first()

        if attendance:
            # ✅ Update the existing attendance record
            if check_type == 'check_in':
                attendance.check_in_time = check_in_time
            elif check_type == 'check_out':
                attendance.check_out_time = check_out_time

            attendance.source = 'request'
            attendance.save()
        else:
            # ➕ Create a new attendance record
            attendance = Attendance.objects.create(
                user=user,  # the person marking attendance (admin/supervisor)
                attendee=user,  # the person whose attendance is being marked
                check_in_time=check_in_time if check_type == 'check_in' else None,
                check_out_time=check_out_time if check_type == 'check_out' else None,
                source='request'  # source = "request" means requested by staff
            )

        # 🔗 Link this attendance record to the request
        validated_data['attendance'] = attendance

        # 💾 Create and return the AttendanceRequest object
        return super().create(validated_data)
        
from rest_framework import serializers
from .models import Attendance, AttendanceRequest
from preferences.models import Setting 
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils.timezone import localtime,localdate
from django.utils.timezone import is_naive, make_aware
class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = [
            'id', 'attendee', 'check_in_time', 'check_out_time',
            'check_in_gap', 'check_out_gap', 'latitude', 'longitude',
            'attachment', 'source', 'created_at', 'user'
        ]
        read_only_fields = [
            'user', 'check_in_gap', 'check_out_gap', 'created_at', 'source'
        ]

    # -------------------
    # Field-level validation
    # -------------------
    def validate_latitude(self, value):
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    # -------------------
    # Object-level validation
    # -------------------
    def validate(self, data):
        request = self.context['request']
        user = request.user

        # ✅ Determine the date from check-in/check-out
        record_date = None
        if data.get('check_in_time'):
            record_date = localdate(data['check_in_time'])
        elif data.get('check_out_time'):
            record_date = localdate(data['check_out_time'])

        if record_date:
            existing_qs = Attendance.objects.filter(user=user).filter(
                check_in_time__date=record_date
            ) | Attendance.objects.filter(user=user).filter(
                check_out_time__date=record_date
            )

            # Exclude current record if updating
            if self.instance:
                existing_qs = existing_qs.exclude(pk=self.instance.pk)

            if existing_qs.exists():
                existing_record = existing_qs.first()

                # ✅ If record exists with check_in_time but no check_out_time → attach it
                if existing_record.check_in_time and not existing_record.check_out_time and data.get('check_out_time'):
                    existing_record.check_out_time = data['check_out_time']
                    existing_record.save()
                    raise serializers.ValidationError(
                        f"Check-out time has been recorded for {record_date} in the existing attendance."
                    )

                # Otherwise, block duplicate entry
                raise serializers.ValidationError(
                    f"Attendance for {record_date} already exists."
                )

        # ✅ Require at least one time
        if not data.get('check_in_time') and not data.get('check_out_time'):
            raise serializers.ValidationError(
                "At least one of check-in time or check-out time must be provided."
            )

        # ✅ Prevent invalid time sequence
        if data.get('check_in_time') and data.get('check_out_time'):
            if data['check_out_time'] < data['check_in_time']:
                raise serializers.ValidationError(
                    "Check-out time cannot be before check-in time."
                )

        return data
    # -------------------
    # Gap calculation helper
    # -------------------
     # ------------------------------------------------
    # HELPER: Fetch company opening/closing times
    # ------------------------------------------------
    # -------------------
    # Company timings fetch
    # -------------------
    def _get_company_times(self):
        """Fetch opening & closing times from Setting JSONField."""
        setting = Setting.objects.filter(slug="company_timmings_both", user=None).first()
        if not setting or not isinstance(setting.value, dict):
            return None
        return setting.value

    # -------------------
    # GAP Calculations
    # -------------------
    def get_check_in_gap(self, obj):
        timings = self._get_company_times()
        if not timings or not obj.check_in_time:
            return None
        try:
            opening_time = datetime.strptime(
                timings.get("opening-time") or timings.get("opening_time"),
                "%H:%M"
            ).time()
        except Exception:
            return None
        company_opening_dt = make_aware(datetime.combine(obj.check_in_time.date(), opening_time))
        gap = obj.check_in_time - company_opening_dt
        return round(gap.total_seconds() / 60, 2)

    def get_check_out_gap(self, obj):
        timings = self._get_company_times()
        if not timings or not obj.check_out_time:
            return None
        try:
            closing_time = datetime.strptime(
                timings.get("closing-time") or timings.get("closing_time"),
                "%H:%M"
            ).time()
        except Exception:
            return None
        company_closing_dt = make_aware(datetime.combine(obj.check_out_time.date(), closing_time))
        gap = obj.check_out_time - company_closing_dt
        return round(gap.total_seconds() / 60, 2)

    # -------------------
    # Save hooks
    # -------------------
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
     # # -------------------
    # # Create method
    # # -------------------
    # def create(self, validated_data):
    #     validated_data['user'] = self.context['request'].user
    #     instance = super().create(validated_data)
    #     print("🛠 Running gap calculation in create()...")
    #     self._calculate_gaps(instance)
    #     instance.save()
    #     return instance

    # # -------------------
    # # Update method
    # # -------------------
    # def update(self, instance, validated_data):
    #     instance = super().update(instance, validated_data)
    #     # print("🛠 Running gap calculation in update()...")
    #     # self._calculate_gaps(instance)
    #     instance.save()
    #     return instance
        
# class AttendanceRequestSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AttendanceRequest
#         fields = '__all__'
#         read_only_fields = [
#             'user', 'status', 'check_in_gap',
#             'check_out_gap', 'created_at', 'updated_at'
#         ]
        
#     def create(self, validated_data):
#         # 👤 Set the user from the request context (ignore input from client)
#         user = self.context['request'].user
#         validated_data['user'] = user

#         # 🧾 Extract required fields
#         check_type = validated_data.get('check_type')
#         check_in_time = validated_data.get('check_in_time')
#         check_out_time = validated_data.get('check_out_time')

#         # 📅 Determine the target date from check-in or check-out time
#         target_date = None
#         if check_type == 'check_in' and check_in_time:
#             target_date = check_in_time.date()
#         elif check_type == 'check_out' and check_out_time:
#             target_date = check_out_time.date()

#         # 🔍 Check if an attendance already exists for this user on that date
#         attendance = Attendance.objects.filter(
#             attendee=user,
#             check_in_time__date=target_date
#         ).first()

#         if attendance:
#             # ✅ Update the existing attendance record
#             if check_type == 'check_in':
#                 attendance.check_in_time = check_in_time
#             elif check_type == 'check_out':
#                 attendance.check_out_time = check_out_time

#             attendance.source = 'request'
#             attendance.save()
#         else:
#             # ➕ Create a new attendance record
#             attendance = Attendance.objects.create(
#                 user=user,  # the person marking attendance (admin/supervisor)
#                 attendee=user,  # the person whose attendance is being marked
#                 check_in_time=check_in_time if check_type == 'check_in' else None,
#                 check_out_time=check_out_time if check_type == 'check_out' else None,
#                 source='request'  # source = "request" means requested by staff
#             )

#         # 🔗 Link this attendance record to the request
#         validated_data['attendance'] = attendance

#         # 💾 Create and return the AttendanceRequest object
#         return super().create(validated_data)
class AttendanceRequestSerializer(serializers.ModelSerializer):
    # user = serializers.ReadOnlyField(source='user.username')

    # class Meta:
    #     model = AttendanceRequest
    #     fields = '__all__'
    #     read_only_fields = ['user', 'attendance', 'created_at', 'updated_at', 'check_in_gap', 'check_out_gap']

    # def validate(self, data):
    #     check_type = data.get('check_type')
    #     check_in = data.get('check_in_time')
    #     check_out = data.get('check_out_time')

    #     # Validate presence of time fields matching check_type
    #     if check_type == AttendanceRequest.CHECK_IN and not check_in:
    #         raise serializers.ValidationError("check_in_time must be provided for check_in type.")
    #     if check_type == AttendanceRequest.CHECK_OUT and not check_out:
    #         raise serializers.ValidationError("check_out_time must be provided for check_out type.")

    #     # Validate status changes only allowed by admins
    #     if self.instance and 'status' in data:
    #         user = self.context['request'].user
    #         if not user.is_staff and self.instance.status != data['status']:
    #             raise serializers.ValidationError("Only admin users can change the status.")

    #     return data

    # def create(self, validated_data):
    #     user = self.context['request'].user
    #     validated_data['user'] = user

    #     check_type = validated_data.get('check_type')
    #     check_in_time = validated_data.get('check_in_time')
    #     check_out_time = validated_data.get('check_out_time')

    #     target_date = None
    #     if check_type == AttendanceRequest.CHECK_IN and check_in_time:
    #         target_date = check_in_time.date()
    #     elif check_type == AttendanceRequest.CHECK_OUT and check_out_time:
    #         target_date = check_out_time.date()

    #     attendance = Attendance.objects.filter(
    #         attendee=user,
    #         check_in_time__date=target_date
    #     ).first()

    #     if attendance:
    #         if check_type == AttendanceRequest.CHECK_IN:
    #             attendance.check_in_time = check_in_time
    #         elif check_type == AttendanceRequest.CHECK_OUT:
    #             attendance.check_out_time = check_out_time
    #         attendance.source = 'request'
    #         attendance.full_clean()  # enforce model validation here (will raise if invalid on approval)
    #         attendance.save()
    #     else:
    #         attendance = Attendance(
    #             user=user,
    #             attendee=user,
    #             check_in_time=check_in_time if check_type == AttendanceRequest.CHECK_IN else None,
    #             check_out_time=check_out_time if check_type == AttendanceRequest.CHECK_OUT else None,
    #             source='request'
    #         )
    #         attendance.full_clean()
    #         attendance.save()

    #     validated_data['attendance'] = attendance
    #     return super().create(validated_data)

    # def update(self, instance, validated_data):
    #     user = self.context['request'].user
    #     if 'status' in validated_data and not user.is_staff:
    #         raise serializers.ValidationError("Only admin users can update status.")

    #     instance.status = validated_data.get('status', instance.status)
    #     instance.reason = validated_data.get('reason', instance.reason)

    #     # Update times and type (admin override)
    #     instance.check_in_time = validated_data.get('check_in_time', instance.check_in_time)
    #     instance.check_out_time = validated_data.get('check_out_time', instance.check_out_time)
    #     instance.check_type = validated_data.get('check_type', instance.check_type)

    #     instance.save()

    #     # On approval, update/create Attendance and run model validation
    #     if instance.status == AttendanceRequest.STATUS_APPROVED:
    #         target_date = None
    #         if instance.check_type == AttendanceRequest.CHECK_IN and instance.check_in_time:
    #             target_date = instance.check_in_time.date()
    #         elif instance.check_out_time:
    #             target_date = instance.check_out_time.date()

    #         attendance = Attendance.objects.filter(
    #             attendee=instance.user,
    #             check_in_time__date=target_date
    #         ).first()

    #         if attendance:
    #             if instance.check_type == AttendanceRequest.CHECK_IN:
    #                 attendance.check_in_time = instance.check_in_time
    #             elif instance.check_type == AttendanceRequest.CHECK_OUT:
    #                 attendance.check_out_time = instance.check_out_time
    #             attendance.source = 'request'
    #             attendance.full_clean()
    #             attendance.save()
    #         else:
    #             attendance = Attendance(
    #                 user=instance.user,
    #                 attendee=instance.user,
    #                 check_in_time=instance.check_in_time if instance.check_type == AttendanceRequest.CHECK_IN else None,
    #                 check_out_time=instance.check_out_time if instance.check_type == AttendanceRequest.CHECK_OUT else None,
    #                 source='request'
    #             )
    #             attendance.full_clean()
    #             attendance.save()

    #         if not instance.attendance_id:
    #             instance.attendance = attendance
    #             instance.save(update_fields=['attendance'])

    #     return instance
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = AttendanceRequest
        fields = '__all__'
        read_only_fields = ['user', 'attendance', 'created_at', 'updated_at']

    def validate(self, data):
        check_type = data.get('check_type')
        check_in = data.get('check_in_time')
        check_out = data.get('check_out_time')

        # Require time matching the check_type
        if check_type == AttendanceRequest.CHECK_IN and not check_in:
            raise serializers.ValidationError("check_in_time must be provided for check_in type.")
        if check_type == AttendanceRequest.CHECK_OUT and not check_out:
            raise serializers.ValidationError("check_out_time must be provided for check_out type.")

        # Restrict status changes to admin only
        if self.instance and 'status' in data:
            user = self.context['request'].user
            if not user.is_staff and self.instance.status != data['status']:
                raise serializers.ValidationError("Only admin users can change the status.")

        return data
    # -------------------
    # Create method             
    # -------------------       

    # This method handles both creating and updating attendance records based on the request
    # It checks if an attendance record exists for the user on the requested date and updates it
    # If not, it creates a new attendance record                
    # It also runs model validation before saving
    # -------------------           
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['attendance'] = None

        instance = AttendanceRequest(**validated_data)
        instance.full_clean()  # <-- run model validation
        instance.save()
        return instance
    # -------------------               
    # Update method
    # -------------------               
    # This method updates the AttendanceRequest instance
    # It allows only admin users to change the status field     
    # It also runs model validation before saving
    # -------------------           

    def update(self, instance, validated_data):
        user = self.context['request'].user
        if 'status' in validated_data and not user.is_staff:
            raise serializers.ValidationError("Only admin users can update status.")

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.full_clean()  # <-- run model validation
        instance.save()
         # Attendance creation/update only on approval (handled in model's save)
        return instance
    
    #
class AttendanceReportSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    email = serializers.EmailField()
    total_hours = serializers.FloatField()
    report_type = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
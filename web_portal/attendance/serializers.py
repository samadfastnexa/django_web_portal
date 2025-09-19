from rest_framework import serializers
from .models import Attendance, AttendanceRequest, LeaveRequest, Holiday
from preferences.models import Setting 
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils.timezone import localtime,localdate
from django.utils.timezone import is_naive, make_aware
from django.db.models import Q
from .services import mark_attendance
# -----------------------------
# Attendance Serializer
# -----------------------------
class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = [
            'id', 'attendee', 'check_in_time', 'check_out_time',
            'check_in_gap', 'check_out_gap', 'latitude', 'longitude',
            'attachment', 'source', 'created_at', 'user'
        ]
        read_only_fields = ['user', 'check_in_gap', 'check_out_gap', 'created_at', 'source']

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
        user = self.context['request'].user
        attendee = data.get("attendee", user)
        record_date = None
        if data.get("check_in_time"):
            record_date = localdate(data["check_in_time"])
        elif data.get("check_out_time"):
            record_date = localdate(data["check_out_time"])

        if record_date:
            # -------------------
            # Duplicate attendance check
            # -------------------
            existing_qs = Attendance.objects.filter(attendee=attendee).filter(
                Q(check_in_time__date=record_date) | Q(check_out_time__date=record_date)
            )
            if self.instance:
                existing_qs = existing_qs.exclude(pk=self.instance.pk)
            if existing_qs.exists():
                existing = existing_qs.first()
                if existing.check_in_time and not existing.check_out_time and data.get("check_out_time"):
                    pass  # allow completing check_out
                elif user.is_staff or user.is_superuser:
                    pass  # override
                else:
                    raise serializers.ValidationError(f"Attendance for {record_date} already exists.")

            # -------------------
            # Weekend & holiday check
            # -------------------
            if record_date.weekday() in [5, 6]:  # Saturday=5, Sunday=6
                raise serializers.ValidationError("Cannot mark attendance on weekends.")
            if Holiday.objects.filter(date=record_date).exists():
                raise serializers.ValidationError("Cannot mark attendance on holiday.")

            # -------------------
            # Leave check
            # -------------------
            leave_exists = LeaveRequest.objects.filter(
                user=attendee,
                status='approved',
                start_date__lte=record_date,
                end_date__gte=record_date
            ).exists()
            if leave_exists and not (user.is_staff or user.is_superuser):
                raise serializers.ValidationError(f"Cannot mark attendance on approved leave day ({record_date}).")

        return data

    # -------------------
    # GAP Calculation Helpers
    # -------------------
    def _get_company_times(self):
        setting = Setting.objects.filter(slug="company_timmings_both", user=None).first()
        if not setting or not isinstance(setting.value, dict):
            return None
        return setting.value

    def get_check_in_gap(self, obj):
        timings = self._get_company_times()
        if not timings or not obj.check_in_time:
            return None
        try:
            opening_time = datetime.strptime(
                timings.get("opening-time") or timings.get("opening_time"), "%H:%M"
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
                timings.get("closing-time") or timings.get("closing_time"), "%H:%M"
            ).time()
        except Exception:
            return None
        company_closing_dt = make_aware(datetime.combine(obj.check_out_time.date(), closing_time))
        gap = obj.check_out_time - company_closing_dt
        return round(gap.total_seconds() / 60, 2)

    # -------------------
    # Create/Update Hooks
    # -------------------
    def create(self, validated_data):
        user = self.context['request'].user
        attendee = validated_data.get("attendee", user)
        validated_data["attendee"] = attendee  # Ensure attendee is in validated_data
        record_date = None
        if validated_data.get("check_in_time"):
            record_date = localdate(validated_data["check_in_time"])
        elif validated_data.get("check_out_time"):
            record_date = localdate(validated_data["check_out_time"])

        # Auto-complete checkout if partial exists
        if record_date:
            existing = Attendance.objects.filter(attendee=attendee).filter(
                Q(check_in_time__date=record_date) | Q(check_out_time__date=record_date)
            ).first()
            if existing and not existing.check_out_time and validated_data.get("check_out_time"):
                existing.check_out_time = validated_data["check_out_time"]
                existing.save()
                return existing

        # Default create
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user = self.context['request'].user
        if not (user.is_staff or user.is_superuser):
            validated_data["user"] = user
        return super().update(instance, validated_data)
    
# Duplicate AttendanceSerializer removed - using the main one above with attendee field


# class AttendanceRequestSerializer(serializers.ModelSerializer):
#     user = serializers.ReadOnlyField(source='user.username')
#     attendance = AttendanceSerializer(read_only=True)  # Nested serializer, read-only

#     class Meta:
#         model = AttendanceRequest
#         fields = '__all__'
#         read_only_fields = ['user', 'attendance', 'created_at', 'updated_at']

#     def validate(self, data):
#         user = self.context['request'].user
#         check_type = data.get('check_type') or getattr(self.instance, "check_type", None)
#         check_in = data.get('check_in_time') or getattr(self.instance, "check_in_time", None)
#         check_out = data.get('check_out_time') or getattr(self.instance, "check_out_time", None)

#         # 1️⃣ Require corresponding time
#         if check_type == AttendanceRequest.CHECK_IN and not check_in:
#             raise serializers.ValidationError("check_in_time must be provided for check_in type.")
#         if check_type == AttendanceRequest.CHECK_OUT and not check_out:
#             raise serializers.ValidationError("check_out_time must be provided for check_out type.")

#         # 2️⃣ Status change restrictions
#         if self.instance and 'status' in data:
#             new_status = data['status']
#             old_status = self.instance.status

#             if not user.is_staff and new_status != old_status:
#                 raise serializers.ValidationError("Only admin/staff users can change the status.")

#             if not self.instance.can_transition_to(new_status):
#                 raise serializers.ValidationError(f"Invalid status transition: {old_status} → {new_status}")

#         # 3️⃣ Weekend/Holiday restriction
#         record_date = check_in.date() if check_in else (check_out.date() if check_out else None)
#         if record_date and not (user.is_staff or user.is_superuser):
#             if record_date.weekday() in [5, 6]:
#                 raise serializers.ValidationError("Cannot mark attendance on weekends.")
#             if Holiday.objects.filter(date=record_date).exists():
#                 raise serializers.ValidationError("Cannot mark attendance on holiday.")

#         # 4️⃣ Leave check
#         if record_date and not (user.is_staff or user.is_superuser):
#             leave_exists = LeaveRequest.objects.filter(
#                 user=user,
#                 status='approved',
#                 start_date__lte=record_date,
#                 end_date__gte=record_date
#             ).exists()
#             if leave_exists:
#                 raise serializers.ValidationError("Cannot mark attendance on approved leave day.")

#         return data

#     def create(self, validated_data):
#         instance = super().create(validated_data)
#         # Sync attendance if approved
#         if instance.status == AttendanceRequest.STATUS_APPROVED:
#             self._sync_attendance(instance)
#         return instance

#     def update(self, instance, validated_data):
#         new_status = validated_data.get("status", instance.status)
#         instance = super().update(instance, validated_data)
#         # Sync attendance if approved
#         if new_status == AttendanceRequest.STATUS_APPROVED:
#             self._sync_attendance(instance)
#         return instance

#     def _sync_attendance(self, request_instance):
#         """
#         Syncs AttendanceRequest with the actual Attendance record using mark_attendance.
#         """
#         # Determine timestamp and type
#         if request_instance.check_type == AttendanceRequest.CHECK_IN:
#             check_type = AttendanceRequest.CHECK_IN
#             timestamp = request_instance.check_in_time
#         else:
#             check_type = AttendanceRequest.CHECK_OUT
#             timestamp = request_instance.check_out_time

#         attendance = mark_attendance(
#             user=request_instance.user,
#             attendee=request_instance.user,
#             check_type=check_type,
#             timestamp=timestamp,
#             latitude=getattr(request_instance, "latitude", None),
#             longitude=getattr(request_instance, "longitude", None),
#             attachment=getattr(request_instance, "attachment", None),
#         )

#         # Link the attendance to the request
#         request_instance.attendance = attendance
#         request_instance.save(update_fields=["attendance"])
#         return attendance
class AttendanceRequestSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    attendance = AttendanceSerializer(read_only=True)  # Nested serializer, read-only

    class Meta:
        model = AttendanceRequest
        fields = '__all__'
        read_only_fields = ['user', 'attendance', 'created_at', 'updated_at']

    def validate(self, data):
            user = self.context['request'].user
            check_type = data.get('check_type') or getattr(self.instance, "check_type", None)
            check_in = data.get('check_in_time') or getattr(self.instance, "check_in_time", None)
            check_out = data.get('check_out_time') or getattr(self.instance, "check_out_time", None)

            # 1️⃣ Require corresponding time
            if check_type == AttendanceRequest.CHECK_IN and not check_in:
                raise serializers.ValidationError("check_in_time must be provided for check_in type.")
            if check_type == AttendanceRequest.CHECK_OUT and not check_out:
                raise serializers.ValidationError("check_out_time must be provided for check_out type.")

            # 2️⃣ Clear opposite time field based on check_type
            if check_type == AttendanceRequest.CHECK_IN:
                data['check_out_time'] = None
            elif check_type == AttendanceRequest.CHECK_OUT:
                data['check_in_time'] = None

            # 3️⃣ Prevent multiple requests of the SAME TYPE for the same date
            record_date = None
            if check_in:
                record_date = check_in.date()
            elif check_out:
                record_date = check_out.date()
            
            if record_date and not self.instance:  # Only for new requests
                existing_requests = AttendanceRequest.objects.filter(
                    user=user,
                    check_type=check_type,
                    created_at__date=record_date
                ).exclude(status=AttendanceRequest.STATUS_REJECTED)  # Rejected is allowed

                if existing_requests.exists():
                    raise serializers.ValidationError(
                        f"You already have a {check_type} request for {record_date}. "
                        f"Only one {check_type} request per date is allowed."
                    )

            # 4️⃣ Status change restrictions
            if self.instance and 'status' in data:
                new_status = data['status']
                old_status = self.instance.status

                if not user.is_staff and new_status != old_status:
                    raise serializers.ValidationError("Only admin/staff users can change the status.")

                if not self.instance.can_transition_to(new_status):
                    raise serializers.ValidationError(f"Invalid status transition: {old_status} → {new_status}")

            # 5️⃣ Weekend/Holiday restriction
            if record_date and not (user.is_staff or user.is_superuser):
                if record_date.weekday() in [5, 6]:
                    raise serializers.ValidationError("Cannot mark attendance on weekends.")
                if Holiday.objects.filter(date=record_date).exists():
                    raise serializers.ValidationError("Cannot mark attendance on holiday.")

            # 6️⃣ Leave check
            if record_date and not (user.is_staff or user.is_superuser):
                leave_exists = LeaveRequest.objects.filter(
                    user=user,
                    status='approved',
                    start_date__lte=record_date,
                    end_date__gte=record_date
                ).exists()
                if leave_exists:
                    raise serializers.ValidationError("Cannot mark attendance on approved leave day.")

            return data

    def create(self, validated_data):
        instance = super().create(validated_data)
        # Sync attendance if approved
        if instance.status == AttendanceRequest.STATUS_APPROVED:
            self._sync_attendance(instance)
        return instance

    def update(self, instance, validated_data):
        new_status = validated_data.get("status", instance.status)
        instance = super().update(instance, validated_data)
        # Sync attendance if approved
        if new_status == AttendanceRequest.STATUS_APPROVED:
            self._sync_attendance(instance)
        return instance

    def _sync_attendance(self, request_instance):
        """
        Syncs AttendanceRequest with the actual Attendance record using mark_attendance.
        """
        # Determine timestamp and type
        if request_instance.check_type == AttendanceRequest.CHECK_IN:
            check_type = AttendanceRequest.CHECK_IN
            timestamp = request_instance.check_in_time
        else:
            check_type = AttendanceRequest.CHECK_OUT
            timestamp = request_instance.check_out_time

        attendance = mark_attendance(
            user=request_instance.user,
            attendee=request_instance.user,
            check_type=check_type,
            timestamp=timestamp,
            latitude=getattr(request_instance, "latitude", None),
            longitude=getattr(request_instance, "longitude", None),
            attachment=getattr(request_instance, "attachment", None),
        )

        # Link the attendance to the request
        request_instance.attendance = attendance
        request_instance.save(update_fields=["attendance"])
        return attendance
    
class EmptySerializer(serializers.Serializer):
    """Used for Swagger to show no input fields"""
    pass
class AttendanceReportSerializer(serializers.ModelSerializer):
    total_hours = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            "attendee",
            "day",
            "check_in_time",
            "check_out_time",
            "check_in_gap",
            "check_out_gap",
            "total_hours",
        ]

    def get_total_hours(self, obj):
        if obj.check_in_time and obj.check_out_time:
            return obj.check_out_time - obj.check_in_time
        return None

    def get_day(self, obj):
        return obj.check_in_time.date() if obj.check_in_time else obj.created_at.date()
    
class LeaveRequestSerializer(serializers.ModelSerializer):
        user = serializers.ReadOnlyField(source='user.username')

        class Meta:
            model = LeaveRequest
            fields = '__all__'
            read_only_fields = ['user', 'status', 'created_at', 'updated_at']

        def validate(self, data):
            user = self.context['request'].user
            leave_type = data.get('leave_type')
            profile = getattr(user, 'sales_profile', None)

            if profile:
                quota_map = {
                    'sick': profile.sick_leave_quota,
                    'casual': profile.casual_leave_quota,
                    'other': profile.others_leave_quota
                }
                remaining = quota_map.get(leave_type, 0)
                if remaining <= 0:
                    raise serializers.ValidationError(f"No {leave_type} leave quota left.")

            # Check overlapping leaves
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            overlaps = LeaveRequest.objects.filter(
                user=user,
                status='approved',
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            if overlaps.exists():
                raise serializers.ValidationError("Overlapping leave exists.")

            return data

        def create(self, validated_data):
            validated_data['user'] = self.context['request'].user
            return super().create(validated_data)
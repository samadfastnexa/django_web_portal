from django.contrib import admin
from .models import Attendance, AttendanceRequest

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'user_id', 'attendee_id', 'check_in_time', 'check_out_time',
        'check_in_gap', 'check_out_gap', 'location', 'created_at'
    ]
    readonly_fields = ['check_in_gap', 'check_out_gap', 'created_at']
    list_filter = ['created_at', 'user_id']
    search_fields = ['user_id__email', 'attendee_id', 'location']


@admin.register(AttendanceRequest)
class AttendanceRequestAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'check_in_time', 'check_out_time', 'can_check_in_display',
        'status', 'reason', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'reason']
    readonly_fields = ['created_at', 'updated_at', 'check_in_gap', 'check_out_gap']

    def can_check_in_display(self, obj):
        return obj.can_check_in
    can_check_in_display.boolean = True
    can_check_in_display.short_description = 'Can Check In'

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        # 🚫 If the user lacks approval permission, make 'status' read-only
        if not request.user.is_superuser and (
            not request.user.role or
            not request.user.role.permissions.filter(codename="approve_attendance_request").exists()
        ):
            fields.append('status')

        return fields

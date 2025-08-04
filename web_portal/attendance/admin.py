from django.contrib import admin
from .models import Attendance, AttendanceRequest

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('attendee', 'user', 'check_in_time', 'check_out_time', 'source')
    list_filter = ('source', 'created_at')
    search_fields = ('attendee__username', 'user__username')

    


@admin.register(AttendanceRequest)
class AttendanceRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'check_type', 'attendance', 'created_at']
    fields = ['user', 'check_type', 'check_in_time', 'check_out_time', 'reason', 'attendance']

    def save_model(self, request, obj, form, change):
        # Custom logic to auto-create/update Attendance
        user = obj.user
        check_type = obj.check_type
        check_in_time = obj.check_in_time
        check_out_time = obj.check_out_time

        # Use check_in_time or check_out_time to detect date
        target_date = check_in_time.date() if check_type == 'check_in' and check_in_time else \
                      check_out_time.date() if check_out_time else None

        if target_date:
            attendance = Attendance.objects.filter(
                attendee=user,
                check_in_time__date=target_date
            ).first()

            if attendance:
                if check_type == 'check_in':
                    attendance.check_in_time = check_in_time
                elif check_type == 'check_out':
                    attendance.check_out_time = check_out_time
                attendance.source = 'request'
                attendance.save()
            else:
                attendance = Attendance.objects.create(
                    user=user,
                    attendee=user,
                    check_in_time=check_in_time if check_type == 'check_in' else None,
                    check_out_time=check_out_time if check_type == 'check_out' else None,
                    source='request'
                )

            obj.attendance = attendance

        super().save_model(request, obj, form, change)
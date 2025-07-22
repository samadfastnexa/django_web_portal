from django.contrib import admin
from attendance.models import Attendance

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'attendee_id', 'check_in_time', 'check_out_time', 'location', 'created_at']
    list_filter = ['check_in_time', 'check_out_time']
    search_fields = ['user_id__email', 'attendee_id']

admin.site.register(Attendance, AttendanceAdmin)

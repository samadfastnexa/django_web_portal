from django.contrib import admin
from .models import Attendance

class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'user_id', 'attendee_id', 'check_in_time', 'check_out_time',
        'check_in_gap', 'check_out_gap', 'location', 'created_at'
    ]
    readonly_fields = ['check_in_gap', 'check_out_gap', 'created_at']  
    list_filter = ['created_at', 'user_id']
    search_fields = ['user_id__email', 'attendee_id__email', 'location']


# admin.site.register(Attendance, AttendanceAdmin)
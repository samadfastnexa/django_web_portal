from django.contrib import admin
from .models import Meeting, FarmerAttendance, MeetingAttachment


class FarmerAttendanceInline(admin.TabularInline):
    model = FarmerAttendance
    extra = 1


class MeetingAttachmentInline(admin.TabularInline):
    model = MeetingAttachment
    extra = 1


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    inlines = [FarmerAttendanceInline, MeetingAttachmentInline]
    list_display = ['id', 'fsm_name', 'date', 'region', 'zone', 'territory', 'total_attendees']
    search_fields = ['fsm_name', 'region', 'zone', 'territory', 'location']
    list_filter = ['region', 'zone', 'territory', 'date']
    ordering = ['-date']


# @admin.register(MeetingAttachment)
# class MeetingAttachmentAdmin(admin.ModelAdmin):
#     list_display = ['meeting', 'file', 'id']
from django.contrib import admin
from .models import Meeting, FarmerAttendance, MeetingAttachment,FieldDay,FieldDayAttendance
class FarmerAttendanceInline(admin.TabularInline):
    model = FarmerAttendance
    extra = 1


class MeetingAttachmentInline(admin.TabularInline):
    model = MeetingAttachment
    extra = 1


# @admin.register(Meeting)
# class MeetingAdmin(admin.ModelAdmin):
#     inlines = [FarmerAttendanceInline, MeetingAttachmentInline]
#     list_display = ['id', 'fsm_name', 'date', 'region', 'zone', 'territory', 'total_attendees']
#     search_fields = ['fsm_name', 'region', 'zone', 'territory', 'location']
#     list_filter = ['region', 'zone', 'territory', 'date']
#     ordering = ['-date']
@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    inlines = [FarmerAttendanceInline, MeetingAttachmentInline]

    list_display = [
        'id',
        'fsm_name',
        'date',
        'region_fk',
        'zone_fk',
        'territory_fk',
        'total_attendees',
    ]

    search_fields = [
        'fsm_name',
        'region_fk__name',
        'zone_fk__name',
        'territory_fk__name',
        'location',
    ]

    list_filter = [
        'region_fk',
        'zone_fk',
        'territory_fk',
        'date',
    ]

    ordering = ['-date']


class FieldDayAttendanceInline(admin.TabularInline):
    model = FieldDayAttendance
    extra = 1
    fields = ('farmer_name', 'contact_number', 'acreage', 'crop')
    readonly_fields = ()

@admin.register(FieldDay)
class FieldDayAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'company_fk', 'territory_fk', 'zone_fk', 'region_fk', 
        'date', 'status', 'user', 'is_active'
    )
    list_filter = ('status', 'company_fk', 'region_fk', 'zone_fk', 'territory_fk', 'is_active')
    search_fields = (
        'id', 'title', 'company_fk__Company_name', 'territory_fk__name', 
        'zone_fk__name', 'region_fk__name', 'user__email'
    )
    readonly_fields = ('id',)
    inlines = [FieldDayAttendanceInline]

@admin.register(FieldDayAttendance)
class FieldDayAttendanceAdmin(admin.ModelAdmin):
    list_display = ('field_day', 'farmer_name', 'contact_number', 'acreage', 'crop')
    search_fields = ('farmer_name', 'contact_number', 'crop')
    list_filter = ('crop',)
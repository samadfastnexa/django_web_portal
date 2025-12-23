from django.contrib import admin
from web_portal.admin import admin_site
from .models import Meeting, FarmerAttendance, MeetingAttachment, FieldDay, FieldDayAttendance, FieldDayAttachment, FieldDayAttendanceCrop
class FarmerAttendanceInline(admin.TabularInline):
    model = FarmerAttendance
    extra = 1


class MeetingAttachmentInline(admin.TabularInline):
    model = MeetingAttachment
    extra = 1


@admin.register(Meeting, site=admin_site)
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
        ('date', admin.DateFieldListFilter),
    ]
    ordering = ['-date']


class FieldDayAttendanceInline(admin.TabularInline):
    model = FieldDayAttendance
    extra = 1
    fields = ('farmer', 'farmer_name', 'contact_number', 'acreage', 'crop')
    readonly_fields = ('farmer_name', 'contact_number')  # Auto-filled from farmer
    autocomplete_fields = ['farmer']  # Enable farmer search
    
    def get_readonly_fields(self, request, obj=None):
        """Make acreage readonly when farmer is linked and has total_land_area"""
        readonly = list(self.readonly_fields)
        return readonly

class FieldDayAttachmentInline(admin.TabularInline):
    model = FieldDayAttachment
    extra = 1

@admin.register(FieldDay, site=admin_site)
class FieldDayAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'company_fk', 'territory_fk', 'zone_fk', 'region_fk', 
        'date', 'total_participants', 'demonstrations_conducted', 'user', 'is_active'
    )
    list_filter = (
        'company_fk', 'region_fk', 'zone_fk', 'territory_fk', 
        ('date', admin.DateFieldListFilter), 'total_participants', 'demonstrations_conducted', 'is_active'
    )
    search_fields = (
        'id', 'title', 'company_fk__Company_name', 'territory_fk__name', 
        'zone_fk__name', 'region_fk__name', 'user__email', 'feedback'
    )
    readonly_fields = ('id',)
    ordering = ['-date']
    inlines = [FieldDayAttendanceInline, FieldDayAttachmentInline]

class FieldDayAttendanceCropInline(admin.TabularInline):
    model = FieldDayAttendanceCrop
    extra = 1
    fields = ['crop_name', 'acreage']


@admin.register(FieldDayAttendance, site=admin_site)
class FieldDayAttendanceAdmin(admin.ModelAdmin):
    list_display = ('field_day', 'farmer_info', 'farmer_name', 'contact_number', 'acreage', 'crop', 'get_crops_display')
    search_fields = ('farmer__farmer_id', 'farmer__first_name', 'farmer__last_name', 'farmer_name', 'contact_number', 'crop')
    list_filter = ('crop', 'farmer__district', 'farmer__village', 'field_day__date')
    autocomplete_fields = ['farmer']
    readonly_fields = ('farmer_name', 'contact_number')  # Auto-filled from farmer
    inlines = [FieldDayAttendanceCropInline]
    fieldsets = (
        ('Farmer Linking', {
            'fields': ('farmer',),
            'description': 'Link to an existing farmer to auto-fill attendee information'
        }),
        ('Attendee Information', {
            'fields': ('farmer_name', 'contact_number', 'acreage', 'crop'),
            'description': 'Attendee details (auto-filled from linked farmer if available)'
        }),
    )
    
    def farmer_info(self, obj):
        """Display farmer ID and name if linked"""
        if obj.farmer:
            return f"{obj.farmer.farmer_id} - {obj.farmer.full_name}"
        return "Manual Entry"
    farmer_info.short_description = "Farmer Link"
    farmer_info.admin_order_field = 'farmer__farmer_id'
    
    def get_crops_display(self, obj):
        """Display all crops for this attendance"""
        crops = obj.crops.all()
        if crops:
            return ", ".join([f"{crop.crop_name} ({crop.acreage})" for crop in crops])
        return "-"
    get_crops_display.short_description = "Crops (New)"


@admin.register(FieldDayAttendanceCrop, site=admin_site)
class FieldDayAttendanceCropAdmin(admin.ModelAdmin):
    list_display = ['attendance', 'crop_name', 'acreage']
    list_filter = ['crop_name']
    search_fields = ['crop_name', 'attendance__farmer_name']

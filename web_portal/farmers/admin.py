from django.contrib import admin
from attendance.models import Attendance
from .models import Farmer, FarmingHistory
from web_portal.admin import admin_site

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'attendee_id', 'check_in_time', 'check_out_time', 'location', 'created_at']
    list_filter = ['check_in_time', 'check_out_time']
    search_fields = ['user_id__email', 'attendee_id']

# admin.site.register(Attendance, AttendanceAdmin)

class FarmingHistoryInline(admin.TabularInline):
    model = FarmingHistory
    extra = 1
    fields = (
        'year', 'season', 'crop_name', 'area_cultivated', 
        'total_yield', 'yield_per_acre', 'input_cost', 
        'market_price', 'total_income', 'profit_loss'
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-year', '-created_at']

@admin.register(Farmer, site=admin_site)
class FarmerAdmin(admin.ModelAdmin):
    list_display = (
        'farmer_id', 'full_name', 'primary_phone', 'village', 'district', 
        'total_land_area', 'education_level', 'registration_date'
    )
    list_filter = (
        'gender', 'education_level',
        'district', 'province', 'registration_date'
    )
    search_fields = (
        'farmer_id', 'first_name', 'last_name', 'name', 'father_name', 'cnic',
        'primary_phone', 'email', 'village', 'tehsil', 'district'
    )
    readonly_fields = ('registration_date', 'last_updated', 'age')
    ordering = ['-id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'farmer_id', 'first_name', 'last_name', 'name', 'father_name',
                'date_of_birth', 'gender', 'cnic'
            )
        }),
        ('Contact Information', {
            'fields': (
                'primary_phone', 'secondary_phone', 'email', 'address',
                'village', 'tehsil', 'district', 'province'
            )
        }),
        ('Education & Farm Details', {
            'fields': ('education_level', 'total_land_area')
        }),
        ('System Information', {
            'fields': (
                'registered_by', 'registration_date',
                'last_updated', 'notes', 'profile_picture'
            ),
            'classes': ('collapse',)
        })
    )
    
    # inlines = [FarmingHistoryInline]  # Removed farming history inline
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    
    def age(self, obj):
        return obj.age
    age.short_description = 'Age'

@admin.register(FarmingHistory, site=admin_site)
class FarmingHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'farmer', 'year', 'season', 'crop_name', 'area_cultivated',
        'total_yield', 'yield_per_acre', 'total_income', 'profit_loss', 'created_at'
    )
    list_filter = (
        'year', 'season', 'crop_name', 'farmer__district', 'farmer__province', 'created_at'
    )
    search_fields = (
        'farmer__farmer_id', 'farmer__first_name', 'farmer__last_name',
        'crop_name', 'farming_practices_used'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('farmer', 'year', 'season', 'crop_name')
        }),
        ('Cultivation Details', {
            'fields': (
                'area_cultivated', 'total_yield', 'yield_per_acre',
                'farming_practices_used'
            )
        }),
        ('Financial Details', {
            'fields': (
                'input_cost', 'market_price', 'total_income', 'profit_loss'
            )
        }),
        ('Additional Information', {
            'fields': ('challenges_faced', 'notes'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('farmer')
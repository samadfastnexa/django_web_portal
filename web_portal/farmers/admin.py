from django.contrib import admin
from attendance.models import Attendance
from .models import Farmer, FarmingHistory

class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_id', 'attendee_id', 'check_in_time', 'check_out_time', 'location', 'created_at']
    list_filter = ['check_in_time', 'check_out_time']
    search_fields = ['user_id__email', 'attendee_id']

# admin.site.register(Attendance, AttendanceAdmin)

class FarmingHistoryInline(admin.TabularInline):
    model = FarmingHistory
    extra = 1
    fields = ('year', 'season', 'crop_name', 'area_cultivated', 'total_yield', 'input_cost', 'total_income')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = (
        'farmer_id', 'full_name', 'primary_phone', 'village', 'district', 
        'total_land_area', 'farming_experience', 'is_active', 'is_verified', 'registration_date'
    )
    list_filter = (
        'is_active', 'is_verified', 'gender', 'education_level', 'farming_experience',
        'farm_ownership_type', 'district', 'province', 'registration_date'
    )
    search_fields = (
        'farmer_id', 'first_name', 'last_name', 'name', 'father_name', 'national_id',
        'primary_phone', 'email', 'village', 'tehsil', 'district'
    )
    readonly_fields = ('registration_date', 'last_updated', 'age')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'farmer_id', 'first_name', 'last_name', 'name', 'father_name',
                'date_of_birth', 'gender', 'national_id'
            )
        }),
        ('Contact Information', {
            'fields': (
                'primary_phone', 'secondary_phone', 'email', 'address',
                'village', 'tehsil', 'district', 'province', 'postal_code'
            )
        }),
        ('Location Coordinates', {
            'fields': (
                'current_latitude', 'current_longitude', 'farm_latitude', 'farm_longitude'
            ),
            'classes': ('collapse',)
        }),
        ('Education & Occupation', {
            'fields': ('education_level', 'occupation_besides_farming')
        }),
        ('Farm Details', {
            'fields': (
                'total_land_area', 'cultivated_area', 'farm_ownership_type',
                'land_documents', 'main_crops_grown', 'farming_methods', 'irrigation_source'
            )
        }),
        ('Farming Experience', {
            'fields': ('farming_experience', 'years_of_farming')
        }),
        ('Financial Information', {
            'fields': ('annual_income_range', 'bank_account_details'),
            'classes': ('collapse',)
        }),
        ('Family Information', {
            'fields': (
                'family_members_count', 'dependents_count', 'family_involved_in_farming'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': (
                'is_active', 'is_verified', 'registered_by', 'registration_date',
                'last_updated', 'notes', 'profile_picture'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [FarmingHistoryInline]
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    
    def age(self, obj):
        return obj.age
    age.short_description = 'Age'

@admin.register(FarmingHistory)
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
from django.contrib import admin
from .models import Dealer, MeetingSchedule, SalesOrder, SalesOrderAttachment
from .models import DealerRequest , Company, Region, Zone, Territory

admin.site.register(Dealer)
admin.site.register(MeetingSchedule)
admin.site.register(SalesOrder)
admin.site.register(SalesOrderAttachment)

# @admin.register(DealerRequest)
# class DealerRequestAdmin(admin.ModelAdmin):
#     list_display = ('name', 'status', 'requested_by', 'reviewed_by', 'created_at', 'reviewed_at')
#     list_filter = ('status', 'created_at')
#     search_fields = ('name', 'requested_by__email', 'reviewed_by__email')
#     readonly_fields = ('requested_by', 'reviewed_by', 'created_at', 'reviewed_at')

#     def save_model(self, request, obj, form, change):
#         if not obj.pk:  # Only set on create, not update
#             obj.requested_by = request.user
#         super().save_model(request, obj, form, change)

@admin.register(DealerRequest)
class DealerRequestAdmin(admin.ModelAdmin):
    list_display = (
        'business_name', 'owner_name', 'status', 'requested_by', 'reviewed_by',
        'filer_status', 'minimum_investment', 'created_at'
    )
    list_filter = ('status', 'filer_status', 'company', 'region', 'zone', 'territory')
    search_fields = ('business_name', 'owner_name', 'requested_by__username', 'cnic_number')
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        if change and not obj.reviewed_by:
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Company)
admin.site.register(Region)
admin.site.register(Zone)
admin.site.register(Territory)
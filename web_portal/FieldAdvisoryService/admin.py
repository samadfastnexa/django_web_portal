from django.contrib import admin
from .models import Dealer, MeetingSchedule, SalesOrder, SalesOrderAttachment
from .models import DealerRequest , Company, Region, Zone, Territory
from sap_integration.sap_client import SAPClient

# admin.site.register(Dealer)
admin.site.register(MeetingSchedule)
admin.site.register(SalesOrder)
admin.site.register(SalesOrderAttachment)





admin.site.register(Company)
admin.site.register(Region)
admin.site.register(Zone)
admin.site.register(Territory)

@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'user_email', 'contact_number', 'company', 'is_active')
    list_select_related = ('user',)
    raw_id_fields = ('user',)

    def user_email(self, obj):
        return obj.user.email if obj.user else '-'
    user_email.short_description = 'Email'
    
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
        if not change:
            sap = SAPClient()
            territory_id = None
            if obj.territory and obj.territory.name:
                territory_id = sap.get_territory_id_by_name(obj.territory.name)
            addr_name = 'Bill To'
            addr_type = 'bo_BillTo'
            country_code = 'PK'
            payload = {
                'Series': 70,
                'CardName': obj.business_name,
                'CardType': 'cCustomer',
                'GroupCode': 100,
                'Address': obj.address or '',
                'Phone1': obj.contact_number,
                'ContactPerson': obj.owner_name,
                'FederalTaxID': obj.cnic_number,
                'AdditionalID': None,
                'OwnerIDNumber': obj.cnic_number,
                'UnifiedFederalTaxID': obj.cnic_number,
                'VatGroup': 'AT1',
                'VatLiable': 'vLiable',
                'U_region': obj.region.name if obj.region else None,
                'U_zone': obj.zone.name if obj.zone else None,
                'U_gov': obj.license_expiry.isoformat() if obj.license_expiry else None,
                'U_fil': obj.filer_status,
                'U_WhatsappMessages': 'YES',
                'BPAddresses': [
                    {
                        'AddressName': addr_name,
                        'AddressName2': None,
                        'AddressName3': None,
                        'City': None,
                        'Country': country_code,
                        'State': None,
                        'Street': (obj.address or '')[:50],
                        'AddressType': addr_type,
                    }
                ],
                'ContactEmployees': [
                    {
                        'Name': obj.owner_name,
                        'Position': None,
                        'MobilePhone': None,
                        'E_Mail': None,
                    }
                ],
            }
            if territory_id is not None:
                payload['Territory'] = territory_id
            try:
                sap.create_business_partner(payload)
            except Exception:
                pass

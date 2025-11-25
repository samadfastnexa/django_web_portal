from django.contrib import admin
from django.contrib import messages
import json
import logging
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
    change_list_template = 'admin/fieldadvisoryservice/dealerrequest/change_list.html'
    change_form_template = 'admin/fieldadvisoryservice/dealerrequest/change_form.html'
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
        # Capture previous status before saving
        prev_status = None
        if change and obj.pk:
            try:
                prev_status = DealerRequest.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
            except Exception:
                prev_status = None
        super().save_model(request, obj, form, change)
        # Call SAP only when transitioning to approved
        if obj.status == 'approved' and prev_status != 'approved':
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
                'DebitorAccount': 'A020301001',
                'U_leg': '17-5349',
                'U_gov': obj.license_expiry.isoformat() if obj.license_expiry else None,
                'U_fil': obj.filer_status,
                'U_lic': obj.govt_license_number,
                'U_region': obj.region.name if obj.region else None,
                'U_zone': obj.zone.name if obj.zone else None,
                'U_WhatsappMessages': 'YES',
                'VatGroup': 'AT1',
                'VatLiable': 'vLiable',
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
                try:
                    print("SAP Business Partner payload:", json.dumps(payload, ensure_ascii=False), flush=True)
                except Exception:
                    pass
                result = sap.create_business_partner(payload)
                summary = None
                card_code = None
                if isinstance(result, dict):
                    card_code = result.get('CardCode') or result.get('code')
                    if not card_code:
                        hdrs = result.get('headers') if isinstance(result.get('headers'), dict) else None
                        if hdrs:
                            loc = hdrs.get('Location') or hdrs.get('location')
                            if isinstance(loc, str):
                                try:
                                    # e.g., /b1s/v2/BusinessPartners('BIC00001')
                                    start = loc.find("BusinessPartners('")
                                    if start != -1:
                                        start += len("BusinessPartners('")
                                        end = loc.find("')", start)
                                        if end != -1:
                                            card_code = loc[start:end]
                                except Exception:
                                    pass
                    if card_code:
                        summary = f"CardCode={card_code}"
                try:
                    msg_json = json.dumps(result, ensure_ascii=False)
                except Exception:
                    msg_json = str(result)
                try:
                    logging.getLogger('sap').info(msg_json)
                except Exception:
                    pass
                try:
                    print("SAP Business Partner response:", msg_json, flush=True)
                    if isinstance(result, dict):
                        b = result.get('body')
                        if b:
                            print("SAP Business Partner raw body:", b, flush=True)
                        h = result.get('headers')
                        if h:
                            try:
                                print("SAP Business Partner headers:", json.dumps(h, ensure_ascii=False), flush=True)
                            except Exception:
                                print("SAP Business Partner headers:", str(h), flush=True)
                except Exception:
                    pass
                if len(msg_json) > 800:
                    msg_json = msg_json[:800] + '...'
                if summary:
                    messages.success(request, f"SAP Business Partner created ({summary}). Response: {msg_json}")
                else:
                    messages.success(request, f"SAP Business Partner created. Response: {msg_json}")
            except Exception as e:
                try:
                    logging.getLogger('sap').error(str(e))
                except Exception:
                    pass
                try:
                    print("SAP Business Partner error:", str(e), flush=True)
                except Exception:
                    pass
                messages.error(request, f"SAP Business Partner creation failed: {str(e)}")

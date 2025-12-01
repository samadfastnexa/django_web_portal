from django.contrib import admin
from django.contrib import messages
import json
import logging
from .models import Dealer, MeetingSchedule, SalesOrder, SalesOrderAttachment
from .models import DealerRequest , Company, Region, Zone, Territory
from sap_integration.sap_client import SAPClient
from django import forms
from django.utils import timezone

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
    actions = ['approve_create_bp']
    readonly_fields = ('created_at',)
    
    class DealerRequestAdminForm(forms.ModelForm):
        sap_Series = forms.IntegerField(required=False, initial=70, label='SAP Series')
        sap_CardName = forms.CharField(required=False, label='SAP CardName')
        sap_CardType = forms.CharField(required=False, initial='cCustomer', label='SAP CardType')
        sap_GroupCode = forms.IntegerField(required=False, initial=100, label='SAP GroupCode')
        sap_Address = forms.CharField(required=False, label='SAP Address')
        sap_Phone1 = forms.CharField(required=False, label='SAP Phone1')
        sap_MobilePhone = forms.CharField(required=False, label='SAP MobilePhone')
        sap_ContactPerson = forms.CharField(required=False, label='SAP ContactPerson')
        sap_FederalTaxID = forms.CharField(required=False, label='SAP FederalTaxID')
        sap_AdditionalID = forms.CharField(required=False, label='SAP AdditionalID')
        sap_OwnerIDNumber = forms.CharField(required=False, label='SAP OwnerIDNumber')
        sap_UnifiedFederalTaxID = forms.CharField(required=False, label='SAP UnifiedFederalTaxID')
        sap_Territory = forms.IntegerField(required=False, label='SAP Territory')
        sap_DebitorAccount = forms.CharField(required=False, initial='A020301001', label='SAP DebitorAccount')
        sap_U_leg = forms.CharField(required=False, initial='17-5349', label='SAP U_leg')
        sap_U_gov = forms.DateField(required=False, label='SAP U_gov (license expiry)')
        sap_U_fil = forms.CharField(required=False, label='SAP U_fil')
        sap_U_lic = forms.CharField(required=False, label='SAP U_lic')
        sap_U_region = forms.CharField(required=False, label='SAP U_region')
        sap_U_zone = forms.CharField(required=False, label='SAP U_zone')
        sap_U_WhatsappMessages = forms.CharField(required=False, initial='YES', label='SAP U_WhatsappMessages')
        sap_VatGroup = forms.CharField(required=False, initial='AT1', label='SAP VatGroup')
        sap_VatLiable = forms.CharField(required=False, initial='vLiable', label='SAP VatLiable')

        class Meta:
            model = DealerRequest
            fields = '__all__'

    form = DealerRequestAdminForm

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            # Prepopulate SAP fields from DealerRequest data
            initial = {
                'sap_CardName': obj.business_name,
                'sap_CardType': 'cCustomer',
                'sap_Address': obj.address or '',
                'sap_Phone1': obj.contact_number,
                'sap_MobilePhone': obj.contact_number,
                'sap_ContactPerson': obj.owner_name,
                'sap_FederalTaxID': obj.cnic_number,
                'sap_AdditionalID': '',
                'sap_OwnerIDNumber': obj.cnic_number,
                'sap_UnifiedFederalTaxID': obj.cnic_number,
                'sap_DebitorAccount': 'A020301001',
                'sap_U_leg': '17-5349',
                'sap_U_gov': obj.license_expiry,
                'sap_U_fil': obj.filer_status,
                'sap_U_lic': obj.govt_license_number,
                'sap_U_region': obj.region.name if obj.region else '',
                'sap_U_zone': obj.zone.name if obj.zone else '',
                'sap_U_WhatsappMessages': 'YES',
                'sap_VatGroup': 'AT1',
                'sap_VatLiable': 'vLiable',
            }
            # Attach to form base class initial
            for k, v in initial.items():
                try:
                    form.base_fields[k].initial = v
                except Exception:
                    pass
        return form

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
            # Use form-provided SAP fields if available
            cd = form.cleaned_data if form is not None else {}
            payload = {
                'Series': int(cd.get('sap_Series') or 70),
                'CardName': cd.get('sap_CardName') or obj.business_name,
                'CardType': cd.get('sap_CardType') or 'cCustomer',
                'GroupCode': int(cd.get('sap_GroupCode') or 100),
                'Address': cd.get('sap_Address') or (obj.address or ''),
                'Phone1': cd.get('sap_Phone1') or obj.contact_number,
                'MobilePhone': cd.get('sap_MobilePhone') or obj.contact_number,
                'ContactPerson': cd.get('sap_ContactPerson') or obj.owner_name,
                'FederalTaxID': (cd.get('sap_FederalTaxID') or obj.cnic_number) or None,
                'AdditionalID': (cd.get('sap_AdditionalID') or '') or None,
                'OwnerIDNumber': (cd.get('sap_OwnerIDNumber') or obj.cnic_number) or None,
                'UnifiedFederalTaxID': (cd.get('sap_UnifiedFederalTaxID') or obj.cnic_number) or None,
                'Territory': cd.get('sap_Territory') or territory_id,
                'DebitorAccount': (cd.get('sap_DebitorAccount') or 'A020301001') or None,
                'U_leg': (cd.get('sap_U_leg') or '17-5349') or None,
                'U_gov': (cd.get('sap_U_gov').isoformat() if cd.get('sap_U_gov') else (obj.license_expiry.isoformat() if obj.license_expiry else None)),
                'U_fil': (cd.get('sap_U_fil') or obj.filer_status) or None,
                'U_lic': (cd.get('sap_U_lic') or obj.govt_license_number) or None,
                'U_region': (cd.get('sap_U_region') or (obj.region.name if obj.region else None)) or None,
                'U_zone': (cd.get('sap_U_zone') or (obj.zone.name if obj.zone else None)) or None,
                'U_WhatsappMessages': (cd.get('sap_U_WhatsappMessages') or 'YES') or None,
                'VatGroup': (cd.get('sap_VatGroup') or 'AT1') or None,
                'VatLiable': (cd.get('sap_VatLiable') or 'vLiable') or None,
                'BPAddresses': [
                    {
                        'AddressName': addr_name,
                        'AddressName2': None,
                        'AddressName3': None,
                        'City': None,
                        'Country': country_code,
                        'State': None,
                        'Street': ((cd.get('sap_Address') or (obj.address or ''))[:50]),
                        'AddressType': addr_type,
                    }
                ],
                'ContactEmployees': [
                    {
                        'Name': cd.get('sap_ContactPerson') or obj.owner_name,
                        'Position': None,
                        'MobilePhone': (cd.get('sap_MobilePhone') or obj.contact_number) or None,
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
                # Prefer full BP details when CardCode is available
                try:
                    details = None
                    if card_code:
                        try:
                            details = sap.get_bp_details(card_code)
                        except Exception:
                            try:
                                details = sap.get_business_partner(card_code)
                            except Exception:
                                details = None
                    msg_json = json.dumps(details if details is not None else result, ensure_ascii=False, indent=2)
                except Exception:
                    try:
                        msg_json = json.dumps(result, ensure_ascii=False, indent=2)
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
                messages.success(request, f"SAP_RESPONSE_JSON:{msg_json}")
                if summary:
                    messages.success(request, f"SAP Business Partner created ({summary}).")
                else:
                    messages.success(request, f"SAP Business Partner created.")
                try:
                    obj.sap_response_json = msg_json
                    obj.sap_response_at = timezone.now()
                    if card_code:
                        obj.sap_card_code = card_code
                    obj.save(update_fields=['sap_response_json','sap_response_at','sap_card_code'])
                except Exception:
                    pass
            except Exception as e:
                try:
                    logging.getLogger('sap').error(str(e))
                except Exception:
                    pass
                try:
                    print("SAP Business Partner error:", str(e), flush=True)
                except Exception:
                    pass
                messages.error(request, f"SAP_RESPONSE_JSON:{str(e)}")
                messages.error(request, f"SAP Business Partner creation failed: {str(e)}")
                try:
                    obj.sap_response_json = str(e)
                    obj.sap_response_at = timezone.now()
                    obj.save(update_fields=['sap_response_json','sap_response_at'])
                except Exception:
                    pass

    def approve_create_bp(self, request, queryset):
        for obj in queryset:
            prev_status = obj.status
            if obj.reviewed_by is None:
                obj.reviewed_by = request.user
            obj.status = 'approved'
            obj.save()
            if prev_status == 'approved':
                continue
            sap = SAPClient()
            territory_id = None
            if obj.territory and obj.territory.name:
                territory_id = sap.get_territory_id_by_name(obj.territory.name)
            payload = {
                'Series': 70,
                'CardName': obj.business_name,
                'CardType': 'cCustomer',
                'GroupCode': 100,
                'Address': obj.address or '',
                'Phone1': obj.contact_number,
                'MobilePhone': obj.contact_number,
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
                        'AddressName': 'Bill To',
                        'AddressName2': None,
                        'AddressName3': None,
                        'City': None,
                        'Country': 'PK',
                        'State': None,
                        'Street': (obj.address or '')[:50],
                        'AddressType': 'bo_BillTo',
                    }
                ],
                'ContactEmployees': [
                    {
                        'Name': obj.owner_name,
                        'Position': None,
                        'MobilePhone': obj.contact_number or None,
                        'E_Mail': None,
                    }
                ],
            }
            if territory_id is not None:
                payload['Territory'] = territory_id
            try:
                result = sap.create_business_partner(payload)
                # Extract CardCode from response
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
                # Prefer full details payload for persisted response
                try:
                    details = None
                    if card_code:
                        try:
                            details = sap.get_bp_details(card_code)
                        except Exception:
                            # Fallback to full GET entity
                            try:
                                details = sap.get_business_partner(card_code)
                            except Exception:
                                details = None
                    msg_json = json.dumps(details if details is not None else result, ensure_ascii=False, indent=2)
                except Exception:
                    try:
                        msg_json = json.dumps(result, ensure_ascii=False, indent=2)
                    except Exception:
                        msg_json = str(result)
                messages.success(request, f"SAP_RESPONSE_JSON:{msg_json}")
                if summary:
                    messages.success(request, f"SAP Business Partner created for request {obj.pk} ({summary}).")
                else:
                    messages.success(request, f"SAP Business Partner created for request {obj.pk}.")
                try:
                    obj.sap_response_json = msg_json
                    obj.sap_response_at = timezone.now()
                    if card_code:
                        obj.sap_card_code = card_code
                    obj.save(update_fields=['sap_response_json','sap_response_at','sap_card_code'])
                except Exception:
                    pass
            except Exception as e:
                messages.error(request, f"SAP_RESPONSE_JSON:{str(e)}")
                messages.error(request, f"SAP Business Partner creation failed for request {obj.pk}: {str(e)}")
                try:
                    obj.sap_response_json = str(e)
                    obj.sap_response_at = timezone.now()
                    obj.save(update_fields=['sap_response_json','sap_response_at'])
                except Exception:
                    pass

    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        custom = [
            path('<int:pk>/approve-add-to-sap/', self.admin_site.admin_view(self.approve_add_view), name='dealerrequest_approve_add_to_sap'),
        ]
        return custom + urls

    def approve_add_view(self, request, pk):
        from django.shortcuts import redirect, get_object_or_404
        obj = get_object_or_404(DealerRequest, pk=pk)
        prev_status = obj.status
        if obj.reviewed_by is None:
            obj.reviewed_by = request.user
        obj.status = 'approved'
        obj.save()
        if prev_status != 'approved':
            self.approve_create_bp(request, queryset=[obj])
        else:
            messages.info(request, f"SAP Business Partner already processed for request {obj.pk} (status approved).")
            # Also fetch and display current BP details if CardCode is known
            try:
                if obj.sap_card_code:
                    sap = SAPClient()
                    try:
                        details = sap.get_bp_details(obj.sap_card_code)
                    except Exception:
                        try:
                            details = sap.get_business_partner(obj.sap_card_code)
                        except Exception:
                            details = None
                    if details is not None:
                        msg_json = json.dumps(details, ensure_ascii=False, indent=2)
                        messages.success(request, f"SAP_RESPONSE_JSON:{msg_json}")
                        try:
                            obj.sap_response_json = msg_json
                            obj.sap_response_at = timezone.now()
                            obj.save(update_fields=['sap_response_json','sap_response_at'])
                        except Exception:
                            pass
            except Exception:
                pass
        return redirect(f'../../{pk}/change/')

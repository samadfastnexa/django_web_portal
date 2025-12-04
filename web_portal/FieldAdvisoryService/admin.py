from django.contrib import admin
from django.contrib import messages
import json
import logging
import os
from .models import Dealer, MeetingSchedule, SalesOrder, SalesOrderLine, SalesOrderAttachment
from .models import DealerRequest , Company, Region, Zone, Territory
from sap_integration.sap_client import SAPClient
from django import forms
from django.utils import timezone
from sap_integration import hana_connect

# admin.site.register(Dealer)
admin.site.register(MeetingSchedule)


def _load_env_file(path: str) -> None:
    """Load environment variables from .env file"""
    try:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    s = line.strip()
                    if s == '' or s.startswith('#') or '=' not in s:
                        continue
                    k, v = s.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if v != '' and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                        v = v[1:-1]
                    if k != '' and not os.environ.get(k):
                        os.environ[k] = v
    except Exception:
        pass


def get_hana_connection():
    """Get HANA database connection"""
    try:
        # Load .env file
        _load_env_file(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
        
        from hdbcli import dbapi
        from preferences.models import Setting
        
        # Get database name from settings
        try:
            db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
            if db_setting and hasattr(db_setting, 'value'):
                # If value is a dict, get the current selected schema
                if isinstance(db_setting.value, dict):
                    schema = list(db_setting.value.values())[0] if db_setting.value else '4B-BIO_APP'
                else:
                    schema = str(db_setting.value)
            else:
                schema = os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP')
        except Exception as e:
            print(f"Error getting schema from settings: {e}")
            schema = os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP')
        
        # Strip quotes if present
        schema = schema.strip('"\'')
        
        # Connection parameters
        host = os.environ.get('HANA_HOST', '').strip()
        port = int(os.environ.get('HANA_PORT', 30015))
        user = os.environ.get('HANA_USER', '').strip()
        password = os.environ.get('HANA_PASSWORD', '').strip()
        
        if not host or not user:
            print(f"Missing HANA credentials: host={bool(host)}, user={bool(user)}")
            return None
        
        # Connect
        print(f"Connecting to HANA: {host}:{port} as {user}, schema={schema}")
        conn = dbapi.connect(address=host, port=port, user=user, password=password)
        
        # Set schema
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()
        
        print("HANA connection successful")
        return conn
    except Exception as e:
        print(f"Error connecting to HANA: {e}")
        import traceback
        traceback.print_exc()
        return None


class SalesOrderForm(forms.ModelForm):
    """Custom form with LOV dropdowns for SAP data"""
    
    class Meta:
        model = SalesOrder
        fields = '__all__'
        widgets = {
            'card_code': forms.Select(attrs={'class': 'sap-customer-lov'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'comments': forms.Textarea(attrs={'rows': 3}),
            'sap_error': forms.Textarea(attrs={'rows': 3}),
            'sap_response_json': forms.Textarea(attrs={'rows': 10, 'style': 'font-family: monospace; font-size: 12px;'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate customer dropdown
        try:
            db = get_hana_connection()
            if db:
                customers = hana_connect.customer_lov(db)
                customer_choices = [('', '--- Select Customer ---')] + [
                    (c['CardCode'], f"{c['CardCode']} - {c['CardName']}") 
                    for c in customers
                ]
                self.fields['card_code'].widget = forms.Select(choices=customer_choices, attrs={'class': 'sap-customer-lov', 'style': 'width: 400px;'})
                db.close()
            else:
                print("Failed to get HANA connection for customers")
        except Exception as e:
            print(f"Error loading customers: {e}")
            import traceback
            traceback.print_exc()
        
        # Add help text
        self.fields['card_code'].help_text = "Select customer from SAP"
        self.fields['card_name'].widget.attrs['readonly'] = True
        self.fields['contact_person_code'].help_text = "Auto-filled from customer"
        self.fields['federal_tax_id'].help_text = "Auto-filled from customer (NTN)"


class SalesOrderLineInlineForm(forms.ModelForm):
    """Custom form for sales order lines with LOV dropdowns"""
    
    class Meta:
        model = SalesOrderLine
        fields = '__all__'
        widgets = {
            'item_code': forms.Select(attrs={'class': 'sap-item-lov'}),
            'warehouse_code': forms.Select(attrs={'class': 'sap-warehouse-lov'}),
            'vat_group': forms.Select(attrs={'class': 'sap-tax-lov'}),
            'project_code': forms.Select(attrs={'class': 'sap-project-lov'}),
            'u_crop': forms.Select(attrs={'class': 'sap-crop-lov'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        try:
            db = get_hana_connection()
            if db:
                # Populate item dropdown
                items = hana_connect.item_lov(db)
                item_choices = [('', '--- Select Item ---')] + [
                    (item['ItemCode'], f"{item['ItemCode']} - {item['ItemName']}") 
                    for item in items[:500]  # Limit to first 500 items for performance
                ]
                self.fields['item_code'].widget = forms.Select(choices=item_choices, attrs={'class': 'sap-item-lov', 'style': 'width: 400px;'})
                
                # Populate tax group dropdown
                tax_codes = hana_connect.sales_tax_codes(db)
                tax_choices = [('', '--- Select Tax ---')] + [
                    (tax['Code'], f"{tax['Code']} - {tax['Name']} ({tax['Rate']}%)") 
                    for tax in tax_codes
                ]
                self.fields['vat_group'].widget = forms.Select(choices=tax_choices, attrs={'class': 'sap-tax-lov', 'style': 'width: 300px;'})
                
                # Populate project dropdown
                projects = hana_connect.projects_lov(db)
                project_choices = [('', '--- Select Project ---')] + [
                    (proj['PrjCode'], f"{proj['PrjCode']} - {proj['PrjName']}") 
                    for proj in projects[:200]  # Limit to first 200 projects
                ]
                self.fields['project_code'].widget = forms.Select(choices=project_choices, attrs={'class': 'sap-project-lov', 'style': 'width: 350px;'})
                
                # Populate crop dropdown
                crops = hana_connect.crop_lov(db)
                crop_choices = [('', '--- Select Crop ---')] + [
                    (crop['Code'], f"{crop['Code']} - {crop['Name']}") 
                    for crop in crops
                ]
                self.fields['u_crop'].widget = forms.Select(choices=crop_choices, attrs={'class': 'sap-crop-lov', 'style': 'width: 250px;'})
                
                # Warehouse dropdown - will be populated dynamically based on item
                self.fields['warehouse_code'].widget = forms.Select(
                    choices=[('', '--- Select Item First ---')],
                    attrs={'class': 'sap-warehouse-lov', 'style': 'width: 250px;'}
                )
                
                db.close()
                print(f"Loaded {len(item_choices)-1} items, {len(tax_choices)-1} tax codes, {len(project_choices)-1} projects, {len(crop_choices)-1} crops")
            else:
                print("Failed to get HANA connection for LOVs")
        except Exception as e:
            print(f"Error loading LOVs: {e}")
            import traceback
            traceback.print_exc()
        
        # Set readonly fields
        self.fields['item_description'].widget.attrs['readonly'] = True
        self.fields['measure_unit'].widget.attrs['readonly'] = True
        self.fields['uom_code'].widget.attrs['readonly'] = True


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    form = SalesOrderLineInlineForm
    extra = 1
    # Reorganized fields for better layout - grouped logically
    fields = (
        'line_num', 
        'item_code', 
        'item_description', 
        'quantity', 
        'measure_unit', 
        'uom_entry',
        'uom_code',
        'unit_price',
        'discount_percent', 
        'warehouse_code', 
        'vat_group', 
        'tax_percentage_per_row',
        'project_code',
        'u_sd', 
        'u_ad', 
        'u_exd', 
        'u_zerop', 
        'u_pl', 
        'u_bp', 
        'u_policy', 
        'u_focitem', 
        'u_crop'
    )
    # Add CSS classes for styling
    classes = ['collapse', 'open']
    
    def get_formset(self, request, obj=None, **kwargs):
        """Customize the formset to add better help text"""
        formset = super().get_formset(request, obj, **kwargs)
        # Add help text to guide users
        if hasattr(formset.form, 'base_fields'):
            formset.form.base_fields['item_code'].help_text = "Select item from catalog"
            formset.form.base_fields['warehouse_code'].help_text = "Select warehouse (based on item)"
            formset.form.base_fields['quantity'].help_text = "Enter quantity"
            formset.form.base_fields['unit_price'].help_text = "Unit price"
            formset.form.base_fields['discount_percent'].help_text = "Discount %"
        return formset


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    form = SalesOrderForm
    list_display = ('id', 'card_code', 'card_name', 'doc_date', 'status', 'is_posted_to_sap', 'sap_doc_num', 'created_at')
    list_filter = ('status', 'is_posted_to_sap', 'doc_date', 'created_at')
    search_fields = ('card_code', 'card_name', 'federal_tax_id', 'u_s_card_code')
    readonly_fields = ('created_at', 'sap_doc_entry', 'sap_doc_num', 'sap_error', 'sap_response_json', 'posted_at', 'is_posted_to_sap', 'add_to_sap_button')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('staff', 'dealer', 'schedule', 'status', 'created_at')
        }),
        ('Document Header', {
            'fields': ('series', 'doc_type', 'doc_date', 'doc_due_date', 'tax_date', 'summery_type', 'doc_object_code')
        }),
        ('Customer Information', {
            'fields': ('card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address')
        }),
        ('Currency & Rates', {
            'fields': ('doc_currency', 'doc_rate')
        }),
        ('Additional Information', {
            'fields': ('comments',)
        }),
        ('User Defined Fields', {
            'fields': ('u_sotyp', 'u_usid', 'u_swje', 'u_secje', 'u_crje', 'u_s_card_code', 'u_s_card_name'),
            'classes': ('collapse',)
        }),
        ('SAP Integration', {
            'fields': ('add_to_sap_button', 'is_posted_to_sap', 'sap_doc_entry', 'sap_doc_num', 'posted_at', 'sap_error', 'sap_response_json'),
        }),
    )
    
    inlines = [SalesOrderLineInline]
    
    actions = ['post_to_sap']
    
    def add_to_sap_button(self, obj):
        """Display a button to post this order to SAP"""
        from django.utils.html import format_html
        from django.urls import reverse
        
        if obj.pk:
            if obj.is_posted_to_sap:
                return format_html(
                    '<div style="padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; color: #155724;">'
                    '<strong>✓ Posted to SAP</strong><br>'
                    'DocEntry: {}<br>DocNum: {}'
                    '</div>',
                    obj.sap_doc_entry, obj.sap_doc_num
                )
            else:
                url = reverse('admin:post_order_to_sap', args=[obj.pk])
                return format_html(
                    '<a class="button" href="{}" style="padding: 10px 15px; background-color: #417690; color: white; '
                    'text-decoration: none; border-radius: 4px; display: inline-block; font-weight: bold;">'
                    'Add to SAP'
                    '</a>',
                    url
                )
        return "-"
    add_to_sap_button.short_description = "SAP Action"
    
    def post_to_sap(self, request, queryset):
        """Action to post selected sales orders to SAP"""
        success_count = 0
        error_count = 0
        
        for order in queryset:
            if order.is_posted_to_sap:
                self.message_user(request, f"Order #{order.id} already posted to SAP", messages.WARNING)
                continue
            
            try:
                # Build SAP payload
                payload = {
                    "Series": order.series,
                    "DocType": order.doc_type,
                    "DocDate": order.doc_date.strftime('%Y-%m-%d') if order.doc_date else None,
                    "DocDueDate": order.doc_due_date.strftime('%Y-%m-%d') if order.doc_due_date else None,
                    "TaxDate": order.tax_date.strftime('%Y-%m-%d') if order.tax_date else None,
                    "CardCode": order.card_code,
                    "CardName": order.card_name,
                    "ContactPersonCode": order.contact_person_code,
                    "FederalTaxID": order.federal_tax_id,
                    "PayToCode": order.pay_to_code,
                    "Address": order.address,
                    "DocCurrency": order.doc_currency,
                    "DocRate": float(order.doc_rate),
                    "Comments": order.comments or "",
                    "SummeryType": order.summery_type,
                    "DocObjectCode": order.doc_object_code,
                    "U_sotyp": order.u_sotyp,
                    "U_USID": order.u_usid,
                    "U_SWJE": order.u_swje,
                    "U_SECJE": order.u_secje,
                    "U_CRJE": order.u_crje,
                    "U_SCardCode": order.u_s_card_code,
                    "U_SCardName": order.u_s_card_name,
                    "DocumentLines": []
                }
                
                # Add document lines
                for line in order.document_lines.all().order_by('line_num'):
                    line_data = {
                        "LineNum": line.line_num,
                        "ItemCode": line.item_code,
                        "ItemDescription": line.item_description,
                        "Quantity": float(line.quantity),
                        "DiscountPercent": float(line.discount_percent),
                        "WarehouseCode": line.warehouse_code,
                        "VatGroup": line.vat_group,
                        "UnitsOfMeasurment": float(line.units_of_measurment),
                        "TaxPercentagePerRow": float(line.tax_percentage_per_row),
                        "UnitPrice": float(line.unit_price),
                        "UoMEntry": line.uom_entry,
                        "MeasureUnit": line.measure_unit,
                        "UoMCode": line.uom_code,
                        "ProjectCode": line.project_code,
                        "U_SD": float(line.u_sd),
                        "U_AD": float(line.u_ad),
                        "U_EXD": float(line.u_exd),
                        "U_zerop": float(line.u_zerop),
                        "U_pl": line.u_pl,
                        "U_BP": float(line.u_bp) if line.u_bp else None,
                        "U_policy": line.u_policy,
                        "U_focitem": line.u_focitem,
                        "U_crop": line.u_crop
                    }
                    payload["DocumentLines"].append(line_data)
                
                # Post to SAP
                sap_client = SAPClient()
                response = sap_client.post('Orders', payload)
                
                # Store complete response
                order.sap_response_json = json.dumps(response, indent=2) if response else None
                
                if response and 'DocEntry' in response:
                    order.sap_doc_entry = response.get('DocEntry')
                    order.sap_doc_num = response.get('DocNum')
                    order.is_posted_to_sap = True
                    order.posted_at = timezone.now()
                    order.sap_error = None
                    order.save()
                    success_count += 1
                    self.message_user(request, f"Order #{order.id} posted successfully. SAP DocNum: {order.sap_doc_num}", messages.SUCCESS)
                else:
                    error_count += 1
                    order.sap_error = "No DocEntry in response"
                    order.save()
                    self.message_user(request, f"Order #{order.id} failed: No DocEntry in response", messages.ERROR)
                    
            except Exception as e:
                error_count += 1
                order.sap_error = str(e)
                order.save()
                self.message_user(request, f"Order #{order.id} failed: {str(e)}", messages.ERROR)
        
        if success_count > 0:
            self.message_user(request, f"{success_count} order(s) posted successfully", messages.SUCCESS)
        if error_count > 0:
            self.message_user(request, f"{error_count} order(s) failed", messages.ERROR)
    
    post_to_sap.short_description = "Post selected orders to SAP"
    
    def get_urls(self):
        """Add custom URL for individual order posting"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/post-to-sap/', 
                 self.admin_site.admin_view(self.post_single_order_to_sap),
                 name='post_order_to_sap'),
        ]
        return custom_urls + urls
    
    def post_single_order_to_sap(self, request, order_id):
        """Handle posting a single order to SAP with async JSON response"""
        from django.shortcuts import redirect
        from django.urls import reverse
        from django.http import JsonResponse
        
        order = SalesOrder.objects.get(pk=order_id)
        
        # Check if already posted
        if order.is_posted_to_sap:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': f"Order #{order.id} is already posted to SAP"
                }, status=400)
            else:
                self.message_user(request, f"Order #{order.id} already posted to SAP", messages.WARNING)
                return redirect(reverse('admin:FieldAdvisoryService_salesorder_change', args=[order_id]))
        
        try:
            # Build SAP payload
            payload = {
                "Series": order.series,
                "DocType": order.doc_type,
                "DocDate": order.doc_date.strftime('%Y-%m-%d') if order.doc_date else None,
                "DocDueDate": order.doc_due_date.strftime('%Y-%m-%d') if order.doc_due_date else None,
                "TaxDate": order.tax_date.strftime('%Y-%m-%d') if order.tax_date else None,
                "CardCode": order.card_code,
                "CardName": order.card_name,
                "ContactPersonCode": order.contact_person_code,
                "FederalTaxID": order.federal_tax_id,
                "PayToCode": order.pay_to_code,
                "Address": order.address,
                "DocCurrency": order.doc_currency,
                "DocRate": float(order.doc_rate),
                "Comments": order.comments or "",
                "SummeryType": order.summery_type,
                "DocObjectCode": order.doc_object_code,
                "U_sotyp": order.u_sotyp,
                "U_USID": order.u_usid,
                "U_SWJE": order.u_swje,
                "U_SECJE": order.u_secje,
                "U_CRJE": order.u_crje,
                "U_SCardCode": order.u_s_card_code,
                "U_SCardName": order.u_s_card_name,
                "DocumentLines": []
            }
            
            # Add document lines
            for line in order.document_lines.all().order_by('line_num'):
                line_data = {
                    "LineNum": line.line_num,
                    "ItemCode": line.item_code,
                    "ItemDescription": line.item_description,
                    "Quantity": float(line.quantity),
                    "DiscountPercent": float(line.discount_percent),
                    "WarehouseCode": line.warehouse_code,
                    "VatGroup": line.vat_group,
                    "UnitsOfMeasurment": float(line.units_of_measurment),
                    "TaxPercentagePerRow": float(line.tax_percentage_per_row),
                    "UnitPrice": float(line.unit_price),
                    "UoMEntry": line.uom_entry,
                    "MeasureUnit": line.measure_unit,
                    "UoMCode": line.uom_code,
                    "ProjectCode": line.project_code,
                    "U_SD": float(line.u_sd),
                    "U_AD": float(line.u_ad),
                    "U_EXD": float(line.u_exd),
                    "U_zerop": float(line.u_zerop),
                    "U_pl": line.u_pl,
                    "U_BP": float(line.u_bp) if line.u_bp else None,
                    "U_policy": line.u_policy,
                    "U_focitem": line.u_focitem,
                    "U_crop": line.u_crop
                }
                payload["DocumentLines"].append(line_data)
            
            # Post to SAP (this is the blocking call that takes 10-20 seconds)
            sap_client = SAPClient()
            response = sap_client.post('Orders', payload)
            
            # Store complete response
            order.sap_response_json = json.dumps(response, indent=2) if response else None
            
            if response and 'DocEntry' in response:
                order.sap_doc_entry = response.get('DocEntry')
                order.sap_doc_num = response.get('DocNum')
                order.is_posted_to_sap = True
                order.posted_at = timezone.now()
                order.sap_error = None
                order.save()
                
                success_message = f"Order #{order.id} posted successfully to SAP"
                
                # Return JSON response for AJAX requests
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': success_message,
                        'doc_entry': order.sap_doc_entry,
                        'doc_num': order.sap_doc_num
                    })
                else:
                    self.message_user(request, 
                        f"✓ {success_message}! DocEntry: {order.sap_doc_entry}, DocNum: {order.sap_doc_num}", 
                        messages.SUCCESS)
            else:
                error_msg = "No DocEntry in SAP response"
                order.sap_error = error_msg
                order.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    }, status=400)
                else:
                    self.message_user(request, f"Order #{order.id} failed: {error_msg}", messages.ERROR)
                
        except Exception as e:
            error_msg = str(e)
            order.sap_error = error_msg
            order.sap_response_json = json.dumps({"error": error_msg}, indent=2)
            order.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=500)
            else:
                self.message_user(request, f"Order #{order.id} failed: {error_msg}", messages.ERROR)
        
        # For non-AJAX requests, redirect back
        return redirect(reverse('admin:FieldAdvisoryService_salesorder_change', args=[order_id]))


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

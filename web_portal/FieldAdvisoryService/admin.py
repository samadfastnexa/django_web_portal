from django.contrib import admin
from django.contrib import messages
import json
import logging
import os
from .models import Dealer, MeetingSchedule, MeetingScheduleAttendance, SalesOrder, SalesOrderLine, SalesOrderAttachment
from .models import DealerRequest , Company, Region, Zone, Territory
from sap_integration.sap_client import SAPClient
from django import forms
from django.utils import timezone
from sap_integration import hana_connect

# admin.site.register(Dealer)
class MeetingScheduleAttendanceInline(admin.TabularInline):
    model = MeetingScheduleAttendance
    extra = 1
    fields = ('farmer', 'farmer_name', 'contact_number', 'acreage', 'crop')
    readonly_fields = ('farmer_name', 'contact_number')
    autocomplete_fields = ['farmer']

@admin.register(MeetingSchedule)
class MeetingScheduleAdmin(admin.ModelAdmin):
    inlines = [MeetingScheduleAttendanceInline]
    list_display = [
        'id',
        'fsm_name',
        'date',
        'region',
        'zone',
        'territory',
        'location',
        'total_attendees',
        'presence_of_zm',
        'presence_of_rsm'
    ]
    search_fields = [
        'fsm_name',
        'region__name',
        'zone__name',
        'territory__name',
        'location',
        'key_topics_discussed'
    ]
    list_filter = [
        'region',
        'zone',
        'territory',
        ('date', admin.DateFieldListFilter),
        'presence_of_zm',
        'presence_of_rsm'
    ]
    ordering = ['-date']


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
            'u_s_card_code': forms.Select(attrs={'class': 'sap-child-customer-lov', 'style': 'width: 400px;'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'comments': forms.Textarea(attrs={'rows': 3}),
            'sap_error': forms.Textarea(attrs={'rows': 3}),
            'sap_response_json': forms.Textarea(attrs={'rows': 18, 'style': 'font-family: monospace; font-size: 12px;'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        print("=== FORM INITIALIZATION DEBUG ===")
        print(f"Available fields: {list(self.fields.keys())}")
        print(f"u_s_card_code field type: {type(self.fields.get('u_s_card_code'))}")
        print(f"u_s_card_code widget type: {type(self.fields.get('u_s_card_code').widget) if 'u_s_card_code' in self.fields else 'N/A'}")
        
        # Populate customer dropdown
        try:
            db = get_hana_connection()
            if db:
                try:
                    customers = hana_connect.customer_codes_all(db, limit=2000)
                except Exception:
                    customers = hana_connect.customer_lov(db)
                customer_choices = [('', '--- Select Customer ---')] + [
                    (c['CardCode'], f"{c['CardCode']} - {c['CardName']}") 
                    for c in customers
                ]
                self.fields['card_code'].widget = forms.Select(choices=customer_choices, attrs={'class': 'sap-customer-lov', 'style': 'width: 400px;'})
                
                # If we have a card_code in the instance, load child customers
                if self.instance and self.instance.card_code:
                    print(f"Loading child customers for existing card_code: {self.instance.card_code}")
                    try:
                        child_customers = hana_connect.child_card_code(db, self.instance.card_code)
                        print(f"Found {len(child_customers)} child customers")
                        child_choices = [('', '--- Select Child Customer ---')] + [
                            (c['CardCode'], f"{c['CardCode']} - {c['CardName']}") 
                            for c in child_customers
                        ]
                        # Set choices on the actual u_s_card_code field
                        if 'u_s_card_code' in self.fields:
                            self.fields['u_s_card_code'].widget.choices = child_choices
                            print(f"Set {len(child_choices)} choices on u_s_card_code widget")
                    except Exception as e:
                        print(f"Error loading child customers: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("No card_code in instance, setting default message")
                    # Set initial empty choices - will be populated via JavaScript when parent is selected
                    if 'u_s_card_code' in self.fields:
                        self.fields['u_s_card_code'].widget.choices = [('', '--- Select Parent Customer First ---')]
                        print("Set default message on u_s_card_code")
                
                db.close()
            else:
                print("Failed to get HANA connection for customers")
        except Exception as e:
            print(f"Error loading customers: {e}")
            import traceback
            traceback.print_exc()
        
        # Set help text on child customer field
        if 'u_s_card_code' in self.fields:
            self.fields['u_s_card_code'].help_text = "Select parent customer first to load child customers"
            print(f"Child customer field widget: {type(self.fields['u_s_card_code'].widget)}")
            print(f"Child customer field widget attrs: {self.fields['u_s_card_code'].widget.attrs}")
            print(f"Child customer field is required: {self.fields['u_s_card_code'].required}")
            print(f"Child customer field is disabled: {self.fields['u_s_card_code'].disabled}")
        else:
            print("WARNING: u_s_card_code field not found in form fields!")
        
        if 'u_s_card_name' in self.fields:
            print(f"Child customer NAME field exists: {type(self.fields['u_s_card_name'].widget)}")
        
        print(f"\n=== FINAL FORM FIELDS ===")
        print(f"Total fields in form: {len(self.fields)}")
        print(f"Field names: {list(self.fields.keys())}")
        
        
        # Add help text and readonly attributes only for fields that exist in the form
        if 'card_code' in self.fields:
            self.fields['card_code'].help_text = "Select customer from SAP"
        if 'card_name' in self.fields:
            self.fields['card_name'].widget.attrs['readonly'] = True
        if 'contact_person_code' in self.fields:
            self.fields['contact_person_code'].help_text = "Auto-filled from customer"
        if 'federal_tax_id' in self.fields:
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
                if 'item_code' in self.fields:
                    self.fields['item_code'].widget = forms.Select(choices=item_choices, attrs={'class': 'sap-item-lov', 'style': 'width: 400px;'})
                    print(f"DEBUG: Item LOV loaded with {len(item_choices)} items")
                
                # Populate tax group dropdown
                tax_codes = hana_connect.sales_tax_codes(db)
                tax_choices = [('', '--- Select Tax ---')] + [
                    (tax['Code'], f"{tax['Code']} - {tax['Name']} ({tax['Rate']}%)") 
                    for tax in tax_codes
                ]
                if 'vat_group' in self.fields:
                    self.fields['vat_group'].widget = forms.Select(choices=tax_choices, attrs={'class': 'sap-tax-lov', 'style': 'width: 300px;'})
                    print(f"DEBUG: Tax LOV loaded with {len(tax_choices)} tax codes")
                else:
                    print("DEBUG: vat_group field not in form fields (expected for inline forms)")
                
                # Populate project dropdown
                projects = hana_connect.projects_lov(db)
                project_choices = [('', '--- Select Project ---')] + [
                    (proj['PrjCode'], f"{proj['PrjCode']} - {proj['PrjName']}") 
                    for proj in projects[:200]  # Limit to first 200 projects
                ]
                if 'project_code' in self.fields:
                    self.fields['project_code'].widget = forms.Select(choices=project_choices, attrs={'class': 'sap-project-lov', 'style': 'width: 350px;'})
                    print(f"DEBUG: Project LOV loaded with {len(project_choices)} projects")
                
                # Populate crop dropdown
                try:
                    crops = hana_connect.crop_lov(db)
                    print(f"DEBUG: Loaded {len(crops) if crops else 0} crops from HANA")
                    if crops:
                        print(f"DEBUG: First crop sample: {crops[0] if len(crops) > 0 else 'None'}")
                    crop_choices = [('', '--- Select Crop ---')] + [
                        (crop['Code'], f"{crop['Code']} - {crop['Name']}") 
                        for crop in crops
                    ]
                    print(f"DEBUG: Created {len(crop_choices)} crop choices")
                    if 'u_crop' in self.fields:
                        self.fields['u_crop'].widget = forms.Select(choices=crop_choices, attrs={'class': 'sap-crop-lov', 'style': 'width: 250px;'})
                        print(f"DEBUG: Crop widget assigned successfully to u_crop field")
                    else:
                        print("DEBUG: u_crop field not found in form fields")
                except Exception as e:
                    print(f"ERROR loading crops: {e}")
                    import traceback
                    traceback.print_exc()
                    # Set empty choices on error
                    if 'u_crop' in self.fields:
                        self.fields['u_crop'].widget = forms.Select(choices=[('', '--- No Crops Available ---')], attrs={'class': 'sap-crop-lov', 'style': 'width: 250px;'})
                
                # Load all warehouses (we'll show all available warehouses)
                # Note: In a real scenario, you might want to filter by item, but for now showing all
                try:
                    # Get a sample warehouse list - you can enhance this to load all warehouses
                    # For now, we'll create a basic list
                    warehouse_choices = [
                        ('', '--- Select Warehouse ---'),
                        ('WH01', 'WH01 - Main Warehouse'),
                        ('WH02', 'WH02 - Secondary Warehouse'),
                        ('WH03', 'WH03 - Regional Warehouse'),
                        ('WH04', 'WH04 - Distribution Center'),
                        ('WH05', 'WH05 - Storage Facility'),
                        ('WH06', 'WH06 - Branch Warehouse'),
                    ]
                    self.fields['warehouse_code'].widget = forms.Select(
                        choices=warehouse_choices,
                        attrs={'class': 'sap-warehouse-lov', 'style': 'width: 250px;'}
                    )
                except Exception as e:
                    print(f"Error loading warehouses: {e}")
                
                db.close()
                print(f"Loaded {len(item_choices)-1} items, {len(tax_choices)-1} tax codes, {len(project_choices)-1} projects, {len(crop_choices)-1} crops")
            else:
                print("Failed to get HANA connection for LOVs")
        except Exception as e:
            print(f"Error loading LOVs: {e}")
            import traceback
            traceback.print_exc()
        
        # Set readonly fields only if they exist in the form
        if 'item_description' in self.fields:
            self.fields['item_description'].widget.attrs['readonly'] = True
        if 'measure_unit' in self.fields:
            self.fields['measure_unit'].widget.attrs['readonly'] = True
        if 'uom_code' in self.fields:
            self.fields['uom_code'].widget.attrs['readonly'] = True


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    form = SalesOrderLineInlineForm
    extra = 1
    # Reorganized fields - hiding line_num, uom_entry, uom_code, vat_group, tax_percentage_per_row
    fields = (
        'u_pl',
        'u_policy',
        'item_code', 
        'item_description', 
        'measure_unit',
        'u_crop',
        'warehouse_code', 
        'quantity', 
        'unit_price',
        'discount_percent',
    )
    readonly_fields = ('item_description', 'measure_unit')
    # Add CSS classes for styling
    classes = ['collapse', 'open']
    
    def get_formset(self, request, obj=None, **kwargs):
        """Customize the formset with proper labels and help text"""
        formset = super().get_formset(request, obj, **kwargs)
        # Update labels and help text only for fields that exist
        if hasattr(formset.form, 'base_fields'):
            if 'u_pl' in formset.form.base_fields:
                formset.form.base_fields['u_pl'].label = 'Policy Link'
            if 'u_policy' in formset.form.base_fields:
                formset.form.base_fields['u_policy'].label = 'Policy'
            if 'item_code' in formset.form.base_fields:
                formset.form.base_fields['item_code'].label = 'Item No'
                formset.form.base_fields['item_code'].help_text = "Select item from catalog"
            if 'u_crop' in formset.form.base_fields:
                formset.form.base_fields['u_crop'].label = 'Crop'
            if 'warehouse_code' in formset.form.base_fields:
                formset.form.base_fields['warehouse_code'].label = 'Warehouse'
                formset.form.base_fields['warehouse_code'].help_text = "Select warehouse (filtered by item)"
            if 'quantity' in formset.form.base_fields:
                formset.form.base_fields['quantity'].label = 'Quantity'
                formset.form.base_fields['quantity'].help_text = "Enter quantity"
            if 'unit_price' in formset.form.base_fields:
                formset.form.base_fields['unit_price'].label = 'Unit Price'
                formset.form.base_fields['unit_price'].help_text = "Unit price from policy"
            if 'discount_percent' in formset.form.base_fields:
                formset.form.base_fields['discount_percent'].label = 'Discount %'
                formset.form.base_fields['discount_percent'].help_text = "Discount percentage"
                formset.form.base_fields['discount_percent'].initial = 0.0
        return formset


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    form = SalesOrderForm
    list_display = ('id', 'card_code', 'card_name', 'doc_date', 'status', 'is_posted_to_sap', 'sap_doc_num', 'created_at')
    list_filter = ('status', 'is_posted_to_sap', 'doc_date', 'created_at')
    search_fields = ('card_code', 'card_name', 'federal_tax_id', 'u_s_card_code')
    readonly_fields = ('created_at', 'sap_doc_entry', 'sap_doc_num', 'sap_error', 'sap_response_json', 'posted_at', 'is_posted_to_sap', 'add_to_sap_button', 'series', 'doc_type', 'summery_type', 'doc_object_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('staff', 'dealer', 'schedule', 'status', 'created_at')
        }),
        ('Document Dates', {
            'fields': ('doc_date', 'doc_due_date', 'tax_date'),
            'description': 'Posting Date, Delivery Date, and Document Date'
        }),
        ('Customer Information', {
            'fields': ('card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address'),
            'description': 'Customer Code, Name, Contact Person, and Billing Address (auto-filled based on Customer Code)'
        }),
        ('Sales Type & Portal User', {
            'fields': ('u_sotyp', 'u_usid'),
            'description': 'Sales Type: 01=Regular, 02=Advance | Portal User ID'
        }),
        ('Child Customer (Optional)', {
            'fields': ('u_s_card_code', 'u_s_card_name'),
            'description': 'Select a child customer if applicable. This dropdown populates automatically when you select a parent customer above.'
        }),
        ('Additional Comments', {
            'fields': ('comments',),
            'classes': ('collapse',)
        }),
        ('SAP Integration', {
            'fields': ('add_to_sap_button', 'is_posted_to_sap', 'sap_doc_entry', 'sap_doc_num', 'posted_at', 'sap_error', 'sap_response_json'),
        }),
    )
    
    inlines = [SalesOrderLineInline]
    
    actions = ['post_to_sap']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Update field labels (only for fields that are editable)
        if 'doc_date' in form.base_fields:
            form.base_fields['doc_date'].label = 'Posting Date'
        if 'doc_due_date' in form.base_fields:
            form.base_fields['doc_due_date'].label = 'Delivery Date'
        if 'tax_date' in form.base_fields:
            form.base_fields['tax_date'].label = 'Document Date'
        if 'card_code' in form.base_fields:
            form.base_fields['card_code'].label = 'Customer Code'
        if 'u_sotyp' in form.base_fields:
            form.base_fields['u_sotyp'].label = 'Sales Type'
        if 'u_usid' in form.base_fields:
            form.base_fields['u_usid'].label = 'Portal User ID'
        if 'u_s_card_code' in form.base_fields:
            form.base_fields['u_s_card_code'].label = 'Child Card Code'
        if 'u_s_card_name' in form.base_fields:
            form.base_fields['u_s_card_name'].label = 'Child Card Name'
        
        # Set initial values for dates to current date (only for new objects)
        if not obj:
            from django.utils import timezone
            today = timezone.now().date()
            if 'doc_date' in form.base_fields:
                form.base_fields['doc_date'].initial = today
            if 'doc_due_date' in form.base_fields:
                form.base_fields['doc_due_date'].initial = today
            if 'tax_date' in form.base_fields:
                form.base_fields['tax_date'].initial = today
            if 'u_sotyp' in form.base_fields:
                form.base_fields['u_sotyp'].initial = '01'
        
        return form
    
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
class _CompanySessionResolver:
    def _get_selected_company(self, request):
        try:
            db_key = request.session.get('selected_db', '4B-BIO')
            schema = '4B-BIO_APP' if db_key == '4B-BIO' else ('4B-ORANG_APP' if db_key == '4B-ORANG' else '4B-BIO_APP')
            comp = Company.objects.filter(name=schema).first() or Company.objects.filter(Company_name=schema).first()
            return comp
        except Exception:
            return None

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin, _CompanySessionResolver):
    list_display = ('name', 'company')
    list_filter = ('company',)
    search_fields = ('name',)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        comp = self._get_selected_company(request)
        return qs.filter(company=comp) if comp else qs

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin, _CompanySessionResolver):
    list_display = ('name', 'region', 'company')
    list_filter = ('region', 'company')
    search_fields = ('name', 'region__name')
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        comp = self._get_selected_company(request)
        return qs.filter(company=comp) if comp else qs

@admin.register(Territory)
class TerritoryAdmin(admin.ModelAdmin, _CompanySessionResolver):
    def region(self, obj):
        return obj.zone.region if obj.zone else None
    region.short_description = 'Region'
    list_display = ('name', 'zone', 'region', 'company')
    list_filter = ('zone', 'zone__region', 'company')
    search_fields = ('name', 'zone__name')
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        comp = self._get_selected_company(request)
        return qs.filter(company=comp) if comp else qs

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
        'business_name', 'owner_name', 'status', 'is_posted_to_sap', 'sap_card_code',
        'requested_by', 'reviewed_by', 'filer_status', 'created_at'
    )
    list_filter = ('status', 'is_posted_to_sap', 'filer_status', 'card_type', 'company', 'region', 'zone', 'territory')
    search_fields = ('business_name', 'owner_name', 'requested_by__username', 'cnic_number', 'sap_card_code', 'email')
    actions = ['approve_create_bp']
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at', 'is_posted_to_sap', 'sap_card_code', 'sap_doc_entry', 'sap_error', 'posted_at', 'sap_response_json')
    
    fieldsets = (
        ('Request Information', {
            'fields': ('requested_by', 'status', 'reason')
        }),
        ('Business Partner Basic Info', {
            'fields': ('business_name', 'owner_name', 'contact_number', 'mobile_phone', 'email')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'country')
        }),
        ('Tax & Legal Information', {
            'fields': ('cnic_number', 'federal_tax_id', 'additional_id', 'unified_federal_tax_id', 'filer_status')
        }),
        ('License Information', {
            'fields': ('govt_license_number', 'license_expiry', 'u_leg')
        }),
        ('Documents', {
            'fields': ('cnic_front', 'cnic_back')
        }),
        ('Territory & Organization', {
            'fields': ('company', 'region', 'zone', 'territory')
        }),
        ('SAP Configuration', {
            'fields': ('sap_series', 'card_type', 'group_code', 'debitor_account', 'vat_group', 'vat_liable', 'whatsapp_messages'),
            'classes': ('collapse',)
        }),
        ('Financial', {
            'fields': ('minimum_investment',)
        }),
        ('Review Information', {
            'fields': ('reviewed_at', 'reviewed_by'),
            'classes': ('collapse',)
        }),
        ('SAP Integration Status', {
            'fields': ('is_posted_to_sap', 'sap_card_code', 'sap_doc_entry', 'sap_error', 'posted_at', 'sap_response_json'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
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
        
        # Call SAP only when transitioning to 'approved' or 'posted_to_sap'
        if obj.status in ['approved', 'posted_to_sap'] and prev_status not in ['approved', 'posted_to_sap'] and not obj.is_posted_to_sap:
            sap = SAPClient()
            territory_id = None
            if obj.territory and obj.territory.name:
                territory_id = sap.get_territory_id_by_name(obj.territory.name)
            
            addr_name = 'Bill To'
            addr_type = 'bo_BillTo'
            
            # Build payload using model fields directly
            payload = {
                'Series': obj.sap_series or 70,
                'CardName': obj.business_name or '',
                'CardType': obj.card_type or 'cCustomer',
                'GroupCode': obj.group_code or 100,
                'Address': (obj.address or '')[:100],
                'Phone1': obj.contact_number or '',
                'MobilePhone': obj.mobile_phone or obj.contact_number or '',
                'ContactPerson': obj.owner_name or '',
                'FederalTaxID': obj.federal_tax_id or obj.cnic_number or None,
                'AdditionalID': obj.additional_id or None,
                'OwnerIDNumber': obj.cnic_number or None,
                'UnifiedFederalTaxID': obj.unified_federal_tax_id or obj.cnic_number or None,
                'Territory': territory_id,
                'DebitorAccount': obj.debitor_account or 'A020301001',
                'U_leg': obj.u_leg or '17-5349',
                'U_gov': obj.license_expiry.isoformat() if obj.license_expiry else None,
                'U_fil': obj.filer_status or None,
                'U_lic': obj.govt_license_number or None,
                'U_region': obj.region.name if obj.region else None,
                'U_zone': obj.zone.name if obj.zone else None,
                'U_WhatsappMessages': obj.whatsapp_messages or 'YES',
                'VatGroup': obj.vat_group or 'AT1',
                'VatLiable': obj.vat_liable or 'vLiable',
                'BPAddresses': [
                    {
                        'AddressName': addr_name,
                        'AddressName2': None,
                        'AddressName3': None,
                        'City': obj.city or None,
                        'Country': obj.country or 'PK',
                        'State': obj.state or None,
                        'Street': (obj.address or '')[:50],
                        'AddressType': addr_type,
                    }
                ],
                'ContactEmployees': [
                    {
                        'Name': obj.owner_name or '',
                        'Position': None,
                        'MobilePhone': obj.mobile_phone or obj.contact_number or None,
                        'E_Mail': obj.email or None,
                    }
                ],
            }
            
            try:
                # Log payload
                try:
                    print("SAP Business Partner payload:", json.dumps(payload, ensure_ascii=False), flush=True)
                except Exception:
                    pass
                
                # Create BP in SAP
                result = sap.create_business_partner(payload)
                summary = None
                card_code = None
                doc_entry = None
                
                if isinstance(result, dict):
                    card_code = result.get('CardCode') or result.get('code')
                    doc_entry = result.get('DocEntry')
                    
                    # Try to extract CardCode from Location header if not in body
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
                
                # Get full BP details if CardCode available
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
                
                # Log response
                try:
                    logging.getLogger('sap').info(msg_json)
                except Exception:
                    pass
                
                try:
                    print("SAP Business Partner response:", msg_json, flush=True)
                except Exception:
                    pass
                
                # Show success message
                messages.success(request, f"SAP_RESPONSE_JSON:{msg_json}")
                if summary:
                    messages.success(request, f"SAP Business Partner created ({summary}).")
                else:
                    messages.success(request, "SAP Business Partner created.")
                
                # Update dealer request with SAP response
                try:
                    obj.sap_response_json = msg_json
                    obj.posted_at = timezone.now()
                    obj.is_posted_to_sap = True
                    obj.status = 'posted_to_sap'
                    if card_code:
                        obj.sap_card_code = card_code
                    if doc_entry:
                        obj.sap_doc_entry = doc_entry
                    obj.sap_error = None  # Clear previous errors
                    obj.save(update_fields=['sap_response_json', 'posted_at', 'is_posted_to_sap', 'status', 'sap_card_code', 'sap_doc_entry', 'sap_error'])
                except Exception as save_err:
                    print(f"Error saving SAP response: {save_err}", flush=True)
                    
            except Exception as e:
                # Log error
                error_msg = str(e)
                try:
                    logging.getLogger('sap').error(error_msg)
                except Exception:
                    pass
                
                try:
                    print("SAP Business Partner error:", error_msg, flush=True)
                except Exception:
                    pass
                
                # Show error message and save to model
                messages.error(request, f"SAP Business Partner creation failed: {error_msg}")
                try:
                    obj.sap_error = error_msg[:500]  # Store first 500 chars
                    obj.save(update_fields=['sap_error'])
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

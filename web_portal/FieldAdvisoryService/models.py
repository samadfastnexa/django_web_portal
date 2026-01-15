from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import UniqueConstraint
from django.core.validators import FileExtensionValidator
from FieldAdvisoryService.validators import (
    cnic_validator, phone_number_validator,
    validate_latitude, validate_longitude,email_validator,validate_image  ,
)
    
class BaseAuditModel(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

class BaseInfoModel(BaseAuditModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    address = models.TextField()
    remarks = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    email = models.EmailField(validators=[email_validator])
    contact_number = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        abstract = True


class Company(BaseInfoModel):
    Company_name = models.CharField(max_length=100)

    def __str__(self):
        return self.Company_name  # or self.name if BaseInfoModel has 'name'
    
    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
    
class Region(models.Model):
    company = models.ForeignKey('Company', on_delete=models.PROTECT, related_name='regions')
    name = models.CharField(max_length=100)  # ✅ Region's own name
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_regions'
    )

    def __str__(self):
        return f"{self.name} ({self.company.name})"

class Zone(models.Model):
    company = models.ForeignKey('Company', on_delete=models.PROTECT)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='zones')
    name = models.CharField(max_length=100)  # ✅ Zone's own name
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_zones'
    )

    def __str__(self):
        return f"{self.name} ({self.region.name} - {self.company.name})"


class Territory(models.Model):
    company = models.ForeignKey('Company', on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='territories')
    name = models.CharField(max_length=100)  # ✅ Territory's own name
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        blank=True, 
        null=True,
        validators=[validate_latitude]
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        blank=True, 
        null=True,
        validators=[validate_longitude]
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_territories'
    )

    def __str__(self):
        return f"{self.name} ({self.zone.name} - {self.company.name})"
    
    class Meta:
        verbose_name = "Territory"
        verbose_name_plural = "Territories"

class Dealer(models.Model):
    FILER_CHOICES = [
        ('01', 'Filer'),
        ('02', 'Non-Filer'),
    ]
    
    CARD_TYPE_CHOICES = [
        ('cCustomer', 'Customer'),
        ('cSupplier', 'Supplier'),
        ('cLid', 'Lead'),
    ]
    
    VAT_LIABLE_CHOICES = [
        ('vLiable', 'Liable'),
        ('vExempted', 'Exempted'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dealer',
        null=True,
        blank=True
    )
    card_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    # ==================== Basic Information ====================
    name = models.CharField(max_length=100, help_text="Contact Person Name / Owner Name")
    business_name = models.CharField(max_length=150, blank=True, null=True, help_text="Business/Company Name (SAP CardName)")
    
    cnic_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[cnic_validator]
    )
    
    # ==================== Contact Information ====================
    email = models.EmailField(max_length=100, blank=True, null=True, validators=[email_validator])
    contact_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_number_validator],
        help_text="Primary Phone Number"
    )
    mobile_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Mobile/WhatsApp Number")

    # ==================== Location ====================
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='dealers')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    territory = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True)

    address = models.TextField()
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=2, default='PK', blank=True, null=True, help_text="Country Code")
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    remarks = models.TextField(blank=True, null=True)

    # ==================== Tax & Legal Information ====================
    federal_tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="NTN Number")
    additional_id = models.CharField(max_length=50, blank=True, null=True, help_text="Additional Tax ID")
    unified_federal_tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Unified Tax ID")
    filer_status = models.CharField(max_length=2, choices=FILER_CHOICES, blank=True, null=True)

    # ==================== License Information ====================
    govt_license_number = models.CharField(max_length=50, blank=True, null=True, help_text="Government License Number (U_lic)")
    license_expiry = models.DateField(blank=True, null=True, help_text="License Expiry Date (U_gov)")
    u_leg = models.CharField(max_length=50, default='17-5349', blank=True, null=True, help_text="Legal Reference")

    # ==================== SAP Configuration ====================
    sap_series = models.IntegerField(default=70, blank=True, null=True, help_text="BP Series Number")
    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES, default='cCustomer', blank=True, null=True)
    group_code = models.IntegerField(default=100, blank=True, null=True, help_text="Customer Group")
    debitor_account = models.CharField(max_length=50, default='A020301001', blank=True, null=True)
    vat_group = models.CharField(max_length=10, default='AT1', blank=True, null=True)
    vat_liable = models.CharField(max_length=10, choices=VAT_LIABLE_CHOICES, default='vLiable', blank=True, null=True)
    whatsapp_messages = models.CharField(max_length=3, default='YES', blank=True, null=True)
    
    # ==================== Financial ====================
    minimum_investment = models.PositiveIntegerField(blank=True, null=True, help_text="Minimum investment amount")

    # ==================== System Fields ====================
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dealers_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # ==================== Documents ====================
    cnic_front_image = models.ImageField(
        upload_to='dealers/cnic_front/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
    )
    cnic_back_image = models.ImageField(
        upload_to='dealers/cnic_back/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
    )
    class Meta:
        constraints = [
            UniqueConstraint(fields=['user'], name='unique_user_dealer')
        ]
        permissions = [
            ('manage_dealers', 'Can add/edit/delete dealers'),
            ('view_dealer_reports', 'Can view dealer reports'),
            ('approve_dealer_requests', 'Can approve dealer requests'),
        ]
        
    def __str__(self):
        return f"{self.name} - {self.company.name}"
    
    def save(self, *args, **kwargs):
        """Auto-sync user flags and keep name derived from linked User"""
        # If user is assigned and is_dealer is False, set it to True
        if self.user and not self.user.is_dealer:
            self.user.is_dealer = True
            self.user.save(update_fields=["is_dealer"])

        # Derive dealer.name from User's first/last name (fallback to username/email)
        if self.user:
            first = getattr(self.user, 'first_name', '') or ''
            last = getattr(self.user, 'last_name', '') or ''
            full = (first + ' ' + last).strip()
            if not full:
                full = getattr(self.user, 'username', None) or getattr(self.user, 'email', '')
            self.name = full
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Auto-unset is_dealer flag when dealer is deleted"""
        user = self.user
        super().delete(*args, **kwargs)
        
        # If user exists and this was their only dealer, unset is_dealer
        if user:
            user.is_dealer = False
            user.save(update_fields=["is_dealer"])

class DealerRequest(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('posted_to_sap', 'Posted to SAP'),
    ]

    FILER_CHOICES = [
        ('01', 'Filer'),
        ('02', 'Non-Filer'),
    ]
    
    CARD_TYPE_CHOICES = [
        ('cCustomer', 'Customer'),
        ('cSupplier', 'Supplier'),
        ('cLid', 'Lead'),
    ]
    
    VAT_LIABLE_CHOICES = [
        ('vLiable', 'Liable'),
        ('vExempted', 'Exempted'),
    ]

    # ==================== Request Information ====================
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dealer_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    reason = models.TextField(help_text="Reason for requesting new dealer", blank=True, null=True)
    
    # ==================== Business Partner Basic Info ====================
    owner_name = models.CharField(max_length=100, blank=True, null=True, help_text="Contact Person Name")
    business_name = models.CharField(max_length=150, blank=True, null=True, help_text="SAP CardName")
    contact_number = models.CharField(
        max_length=20,
        validators=[phone_number_validator],
        blank=True,
        null=True,
        help_text="Primary Phone Number"
    )
    mobile_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Mobile/WhatsApp Number")
    email = models.EmailField(max_length=100, blank=True, null=True, help_text="Contact Email")
    address = models.TextField(blank=True, null=True, help_text="Business Address")
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=2, default='PK', blank=True, null=True, help_text="Country Code (PK)")

    # ==================== Tax & Legal Information ====================
    cnic_number = models.CharField(
        max_length=15,
        validators=[cnic_validator],
        blank=True,
        null=True,
        help_text="Owner CNIC (13 digits)"
    )
    federal_tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="NTN Number")
    additional_id = models.CharField(max_length=50, blank=True, null=True, help_text="Additional Tax ID")
    unified_federal_tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Unified Tax ID")
    filer_status = models.CharField(max_length=2, choices=FILER_CHOICES, blank=True, null=True)
    
    # ==================== License Information ====================
    govt_license_number = models.CharField(max_length=50, blank=True, null=True, help_text="U_lic")
    license_expiry = models.DateField(blank=True, null=True, help_text="U_gov")
    u_leg = models.CharField(max_length=50, default='17-5349', blank=True, null=True, help_text="Legal Reference")
 
    # ==================== Documents ====================
    cnic_front = models.ImageField(
        upload_to='dealer_requests/cnic_front/',
        validators=[validate_image],
        blank=True,
        null=True
    )
    cnic_back = models.ImageField(
        upload_to='dealer_requests/cnic_back/',
        validators=[validate_image],
        blank=True,
        null=True
    )
    
    # ==================== Territory & Organization ====================
    company = models.ForeignKey(Company, on_delete=models.PROTECT, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, blank=True, null=True)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, blank=True, null=True)
    territory = models.ForeignKey(Territory, on_delete=models.PROTECT, blank=True, null=True)
    
    # ==================== SAP Configuration ====================
    sap_series = models.IntegerField(default=70, blank=True, null=True, help_text="BP Series Number")
    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES, default='cCustomer', blank=True, null=True)
    group_code = models.IntegerField(default=100, blank=True, null=True, help_text="Customer Group")
    debitor_account = models.CharField(max_length=50, default='A020301001', blank=True, null=True)
    vat_group = models.CharField(max_length=10, default='AT1', blank=True, null=True)
    vat_liable = models.CharField(max_length=10, choices=VAT_LIABLE_CHOICES, default='vLiable', blank=True, null=True)
    whatsapp_messages = models.CharField(max_length=3, default='YES', blank=True, null=True)
    
    # ==================== Financial ====================
    minimum_investment = models.PositiveIntegerField(help_text="Minimum should be 5 lakh", blank=True, null=True)

    # ==================== Timestamps & Review ====================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dealer_approvals'
    )
    
    # ==================== SAP Integration ====================
    is_posted_to_sap = models.BooleanField(default=False)
    sap_card_code = models.CharField(max_length=64, null=True, blank=True, help_text="Generated BP Code from SAP")
    sap_doc_entry = models.IntegerField(null=True, blank=True, help_text="SAP Document Entry")
    sap_error = models.TextField(null=True, blank=True, help_text="Last SAP Error Message")
    sap_response_json = models.TextField(null=True, blank=True, help_text="Full SAP Response")
    posted_at = models.DateTimeField(null=True, blank=True, help_text="Posted to SAP Timestamp")

    def clean(self):
        min_inv = self.minimum_investment
        if min_inv is not None:  # Only validate if provided
            try:
                if int(min_inv) < 500000:
                    raise ValidationError({'minimum_investment': 'Minimum investment must be at least 5 lakh (500,000).'})
            except (TypeError, ValueError):
                raise ValidationError({'minimum_investment': 'Enter a valid number'})

    def __str__(self):
        return f"{self.business_name} ({self.status}) by {self.owner_name}"

    class Meta:
        verbose_name = "Dealer Request"
        verbose_name_plural = "Dealer Requests"
        permissions = [
            ("approve_dealer_request", "Can approve or reject dealer requests"),
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_status = self.status

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._previous_status = self.status

class MeetingSchedule(models.Model):
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fas_meetings')
    fsm_name = models.CharField(max_length=100, default="Unknown FSM")
    region = models.ForeignKey('FieldAdvisoryService.Region', on_delete=models.SET_NULL, null=True, blank=True, related_name='meeting_schedules_region')
    zone = models.ForeignKey('FieldAdvisoryService.Zone', on_delete=models.SET_NULL, null=True, blank=True, related_name='meeting_schedules_zone')
    territory = models.ForeignKey('FieldAdvisoryService.Territory', on_delete=models.SET_NULL, null=True, blank=True, related_name='meeting_schedules_territory')
    date = models.DateField()
    location = models.CharField(max_length=200)
    total_attendees = models.PositiveIntegerField(default=0)
    key_topics_discussed = models.TextField(default="Not specified")
    presence_of_zm = models.BooleanField(default=False)
    presence_of_rsm = models.BooleanField(default=False)
    feedback_from_attendees = models.TextField(blank=True, null=True)
    suggestions_for_future = models.TextField(blank=True, null=True)
    min_farmers_required = models.PositiveIntegerField(default=5)
    confirmed_attendees = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Meeting on {self.date} at {self.location}"

class MeetingScheduleAttendance(models.Model):
    schedule = models.ForeignKey(MeetingSchedule, related_name='attendees', on_delete=models.CASCADE)
    farmer = models.ForeignKey('farmers.Farmer', on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_attendances')
    farmer_name = models.CharField(max_length=100, blank=True)
    contact_number = models.CharField(max_length=15, blank=True)
    acreage = models.FloatField(default=0.0)
    crop = models.CharField(max_length=100, blank=True)

class SalesOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('entertained', 'Entertained'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    )
    
    DOC_TYPE_CHOICES = (
        ('dDocument_Items', 'Items'),
        ('dDocument_Service', 'Service'),
    )
    
    SUMMERY_TYPE_CHOICES = (
        ('dNoSummary', 'No Summary'),
        ('dSummary', 'Summary'),
    )

    # Existing fields
    portal_order_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        help_text="Unique portal order ID (e.g., SO001, SA002) - Not sent to SAP"
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Optional staff user; defaults to current user if omitted",
    )
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # SAP Document Header Fields
    series = models.IntegerField(default=8, help_text="Series number for document")
    doc_type = models.CharField(max_length=50, choices=DOC_TYPE_CHOICES, default='dDocument_Items')
    doc_date = models.DateField(null=True, blank=True, help_text="Document date")
    doc_due_date = models.DateField(null=True, blank=True, help_text="Document due date")
    tax_date = models.DateField(null=True, blank=True, help_text="Tax date")
    
    # Customer Information
    card_code = models.CharField(max_length=50, null=True, blank=True, help_text="Customer code (BP Code)")
    card_name = models.CharField(max_length=255, null=True, blank=True, help_text="Customer name")
    contact_person_code = models.IntegerField(null=True, blank=True, help_text="Contact person code")
    federal_tax_id = models.CharField(max_length=50, null=True, blank=True, help_text="Customer NTN/Tax ID")
    pay_to_code = models.IntegerField(null=True, blank=True, help_text="Pay to code")
    address = models.TextField(null=True, blank=True, help_text="Billing address")
    
    # Currency and Rates
    doc_currency = models.CharField(max_length=10, default='PKR', help_text="Document currency")
    doc_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0, help_text="Exchange rate")
    
    # Additional Information
    comments = models.TextField(blank=True, null=True, help_text="Order comments/remarks")
    summery_type = models.CharField(max_length=50, choices=SUMMERY_TYPE_CHOICES, default='dNoSummary')
    doc_object_code = models.CharField(max_length=50, default='oOrders', help_text="Document object code")
    
    # User Defined Fields (UDF)
    u_sotyp = models.CharField(max_length=10, null=True, blank=True, help_text="Sales Order Type")
    u_usid = models.CharField(max_length=50, null=True, blank=True, help_text="Portal User ID")
    u_swje = models.CharField(max_length=50, null=True, blank=True, help_text="SWJE")
    u_secje = models.CharField(max_length=50, null=True, blank=True, help_text="SECJE")
    u_crje = models.CharField(max_length=50, null=True, blank=True, help_text="CRJE")
    u_s_card_code = models.CharField(max_length=50, null=True, blank=True, help_text="Child Customer Code")
    u_s_card_name = models.CharField(max_length=255, null=True, blank=True, help_text="Child Customer Name")
    
    # SAP Response Fields
    sap_doc_entry = models.IntegerField(null=True, blank=True, help_text="SAP Document Entry (after posting)")
    sap_doc_num = models.IntegerField(null=True, blank=True, help_text="SAP Document Number (after posting)")
    sap_error = models.TextField(null=True, blank=True, help_text="SAP error message if posting failed")
    sap_response_json = models.TextField(null=True, blank=True, help_text="Complete SAP API response")
    is_posted_to_sap = models.BooleanField(default=False, help_text="Posted to SAP successfully")
    posted_at = models.DateTimeField(null=True, blank=True, help_text="When posted to SAP")

    def save(self, *args, **kwargs):
        """Generate unique portal_order_id before saving"""
        if not self.portal_order_id:
            # Generate portal ID based on status
            prefix = 'SO' if self.status == 'pending' else 'SA'
            
            # Get last order with this prefix
            last_order = SalesOrder.objects.filter(
                portal_order_id__startswith=prefix
            ).order_by('-portal_order_id').first()
            
            if last_order and last_order.portal_order_id:
                # Extract number and increment
                last_num = int(last_order.portal_order_id[2:])
                new_num = last_num + 1
            else:
                new_num = 1
            
            # Generate new ID with zero-padded number
            self.portal_order_id = f"{prefix}{new_num:03d}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        if self.portal_order_id:
            return f"{self.portal_order_id} - {self.card_name} - {self.status}"
        return f"Order #{self.id} - {self.card_name} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Sales Order"
        verbose_name_plural = "Sales Orders"


class SalesOrderLine(models.Model):
    """Sales Order Line Items"""
    sales_order = models.ForeignKey(SalesOrder, related_name='document_lines', on_delete=models.CASCADE)
    line_num = models.IntegerField(help_text="Line number in order")
    
    # Item Information
    item_code = models.CharField(max_length=50, help_text="Item code")
    item_description = models.CharField(max_length=255, help_text="Item description")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, help_text="Quantity")
    
    # Pricing
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, help_text="Unit price")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Discount %")
    
    # Warehouse and Tax
    warehouse_code = models.CharField(max_length=50, help_text="Warehouse code")
    vat_group = models.CharField(max_length=20, help_text="VAT/Tax group code")
    tax_percentage_per_row = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Tax %")
    
    # UoM (Unit of Measurement)
    units_of_measurment = models.DecimalField(max_digits=10, decimal_places=2, default=1.0, help_text="UoM conversion")
    uom_entry = models.IntegerField(help_text="UoM Entry ID")
    measure_unit = models.CharField(max_length=20, help_text="Measure unit name")
    uom_code = models.CharField(max_length=20, help_text="UoM Code")
    
    # Project Information
    project_code = models.CharField(max_length=50, null=True, blank=True, help_text="Project code")
    
    # User Defined Fields for Line
    u_sd = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Special Discount %")
    u_ad = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Additional Discount %")
    u_exd = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Extra Discount %")
    u_zerop = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, help_text="Phase Discount %")
    u_pl = models.IntegerField(null=True, blank=True, help_text="Policy Link")
    u_bp = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Project Balance")
    u_policy = models.CharField(max_length=50, null=True, blank=True, help_text="Policy Code")
    u_focitem = models.CharField(max_length=10, default='No', help_text="FOC Item (Yes/No)")
    u_crop = models.CharField(max_length=50, null=True, blank=True, help_text="Crop Code")
    
    def __str__(self):
        return f"Line {self.line_num}: {self.item_code} - {self.quantity}"
    
    class Meta:
        ordering = ['line_num']
        verbose_name = "Sales Order Line"
        verbose_name_plural = "Sales Order Lines"


class SalesOrderAttachment(models.Model):
    sales_order = models.ForeignKey(SalesOrder, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='sales_order_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

# ==================== Organizational Hierarchy Models ====================

class HierarchyLevel(models.Model):
    """
    Defines the organizational hierarchy levels dynamically.
    Example: CEO (0) → Regional Manager (1) → Zone Manager (2) → Field Staff (3)
    """
    LEVEL_CHOICES = [
        ('ceo', 'CEO'),
        ('regional_manager', 'Regional Manager'),
        ('zone_manager', 'Zone Manager'),
        ('field_staff', 'Field Staff'),
        ('custom', 'Custom'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='hierarchy_levels')
    level_name = models.CharField(max_length=100, help_text="Name of hierarchy level (e.g., CEO, Regional Manager)")
    level_code = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='custom')
    level_order = models.PositiveIntegerField(help_text="Order in hierarchy (0=top, higher=bottom)")
    description = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_hierarchy_levels'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('company', 'level_order')
        ordering = ['level_order']
        verbose_name = "Hierarchy Level"
        verbose_name_plural = "Hierarchy Levels"
    
    def __str__(self):
        return f"{self.level_name} (Order: {self.level_order}) - {self.company.Company_name}"


class UserHierarchy(models.Model):
    """
    Links users to hierarchy levels and their reporting structure.
    Defines: Who reports to whom, at which level, and in which region/zone.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hierarchy_assignment'
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='user_hierarchies')
    hierarchy_level = models.ForeignKey(HierarchyLevel, on_delete=models.PROTECT)
    
    # Reporting Structure
    reports_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports'
    )
    
    # Geo Assignment
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    territory = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hierarchy_assignments_made'
    )
    
    class Meta:
        unique_together = ('user', 'company')
        verbose_name = "User Hierarchy"
        verbose_name_plural = "User Hierarchies"
    
    def __str__(self):
        return f"{self.user.username} - {self.hierarchy_level.level_name} ({self.company.Company_name})"
    
    def clean(self):
        """Validate that reports_to is at a higher level in hierarchy"""
        if self.reports_to and self.hierarchy_level:
            try:
                manager_hierarchy = UserHierarchy.objects.get(user=self.reports_to, company=self.company)
                if manager_hierarchy.hierarchy_level.level_order >= self.hierarchy_level.level_order:
                    raise ValidationError(
                        "Manager must be at a higher hierarchy level (lower order number)."
                    )
            except UserHierarchy.DoesNotExist:
                raise ValidationError("Manager must have a hierarchy assignment in the same company.")
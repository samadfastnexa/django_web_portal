from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import UniqueConstraint
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

class Dealer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dealer',               # ← already different, OK
        null=True,
        blank=True
    )
    card_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    name = models.CharField(max_length=100)
    cnic_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[cnic_validator]
    )
    # email = models.EmailField(validators=[email_validator])
    contact_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_number_validator]
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='dealers')
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    territory = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True)

    address = models.TextField()
    remarks = models.TextField(blank=True, null=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dealers_created'      # ← NEW
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    cnic_front_image = models.ImageField(
        upload_to='dealers/cnic_front/',
        validators=[validate_image],
        # default='dealers/cnic_front/default.jpg'
    )
    cnic_back_image = models.ImageField(
        upload_to='dealers/cnic_back/',
        validators=[validate_image],
        # default='dealers/cnic_back/default.jpg'
    )
    class Meta:
     constraints = [
        UniqueConstraint(fields=['user'], name='unique_user_dealer')
    ]
    def __str__(self):
        return f"{self.name} - {self.company.name}"

class DealerRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    FILER_CHOICES = [
        ('filer', 'Filer'),
        ('non_filer', 'Non-Filer'),
    ]

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dealer_requests'
    )

    owner_name = models.CharField(max_length=100)
    business_name = models.CharField(max_length=150)
    contact_number  = models.CharField(
        max_length=20,
        unique=True,
        validators=[phone_number_validator]
    )
    address = models.TextField(blank=True)

    cnic_number = models.CharField(
        max_length=15,  # Must be 15, NOT 13
        unique=True,
        validators=[cnic_validator]
    )
 
    cnic_front = models.ImageField(
        upload_to='dealer_requests/cnic_front/',
        validators=[validate_image]
    )
    cnic_back = models.ImageField(
        upload_to='dealer_requests/cnic_back/',
        validators=[validate_image]
    )
    govt_license_number = models.CharField(max_length=50)
    license_expiry = models.DateField()

    reason = models.TextField(help_text="Reason for requesting new dealer")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    filer_status = models.CharField(max_length=10, choices=FILER_CHOICES)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT)
    territory = models.ForeignKey(Territory, on_delete=models.PROTECT)
    

    def __str__(self):
        return f"{self.company} - {self.zone} - {self.id}"
    
    minimum_investment = models.PositiveIntegerField(help_text="Minimum should be 5 lakh")

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dealer_approvals'
    )

    def clean(self):
        if self.minimum_investment < 500000:
            raise ValidationError("Minimum investment must be at least 5 lakh (500,000).")

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
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fas_meetings'
    )
    date = models.DateField()
    location = models.CharField(max_length=200)
    min_farmers_required = models.PositiveIntegerField(default=5)
    confirmed_attendees = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Meeting on {self.date} at {self.location}"

class SalesOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('entertained', 'Entertained'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    )

    schedule = models.ForeignKey(MeetingSchedule, on_delete=models.CASCADE)
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order #{self.id} - {self.status}"

class SalesOrderAttachment(models.Model):
    sales_order = models.ForeignKey(SalesOrder, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='sales_order_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Farmer(models.Model):
    # User Account (for login)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='farmer_profile',
        null=True,
        blank=True,
        help_text=_('Associated user account for login')
    )
    GENDER_CHOICES = [
        ('male', _('Male')),
        ('female', _('Female')),
        ('other', _('Other')),
    ]
    
    EDUCATION_CHOICES = [
        ('none', _('No Formal Education')),
        ('primary', _('Primary School')),
        ('secondary', _('Secondary School')),
        ('higher_secondary', _('Higher Secondary')),
        ('diploma', _('Diploma')),
        ('bachelor', _('Bachelor Degree')),
        ('master', _('Master Degree')),
        ('phd', _('PhD')),
    ]
    
    # Personal Information
    farmer_id = models.CharField(max_length=10, unique=True, verbose_name=_('Farmer ID'))
    first_name = models.CharField(max_length=50, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=50, verbose_name=_('Last Name'))
    name = models.CharField(max_length=100, verbose_name=_('Full Name'))  # Keep for backward compatibility
    father_name = models.CharField(max_length=100, blank=True, verbose_name=_('Father Name'))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date of Birth'))
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, verbose_name=_('Gender'))
    cnic = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name=_('CNIC'))
    
    # Contact Information
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    primary_phone = models.CharField(validators=[phone_regex], max_length=17, verbose_name=_('Primary Phone'))
    secondary_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, verbose_name=_('Secondary Phone'))
    email = models.EmailField(blank=True, verbose_name=_('Email Address'))
    
    # Address Information
    address = models.TextField(blank=True, verbose_name=_('Complete Address'))
    village = models.CharField(max_length=100, verbose_name=_('Village'))
    tehsil = models.CharField(max_length=100, verbose_name=_('Tehsil'))
    district = models.CharField(max_length=100, verbose_name=_('District'))
    province = models.CharField(max_length=100, blank=True, verbose_name=_('Province/State'))
    
    # Education
    education_level = models.CharField(max_length=20, choices=EDUCATION_CHOICES, default='primary', verbose_name=_('Education Level'))
    
    # Farm Details
    total_land_area = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text=_('Total land area in acres'), verbose_name=_('Total Land Area (acres)'))
    current_crops_and_acreage = models.TextField(blank=True, null=True, verbose_name=_('Total Current Crops Sown and Acreage'), help_text=_('Details of current crops sown with acreage information'))
    crop_calendar = models.TextField(blank=True, null=True, verbose_name=_('Crop Calendar'), help_text=_('Planned crop calendar and rotation schedule'))
    
    # Registration and Status
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name=_('Registration Date'))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_('Last Updated'))
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_farmers', verbose_name=_('Registered By'))
    
    # Additional Notes
    notes = models.TextField(blank=True, verbose_name=_('Additional Notes'))
    profile_picture = models.ImageField(upload_to='farmer_profiles/', null=True, blank=True, verbose_name=_('Profile Picture'))
    
    class Meta:
        verbose_name = _('Farmer')
        verbose_name_plural = _('Farmers')
        ordering = ['-id']
        indexes = [
            models.Index(fields=['farmer_id']),
            models.Index(fields=['district', 'tehsil']),
            models.Index(fields=['registration_date']),

        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.farmer_id})"
    
    def save(self, *args, **kwargs):
        # Auto-generate full name from first and last name
        self.name = f"{self.first_name} {self.last_name}"
        
        # Auto-generate farmer_id if not provided
        if not self.farmer_id:
            self.farmer_id = self.generate_unique_farmer_id()
        
        # Auto-create User account if not exists
        if not self.user and self.primary_phone:
            try:
                # Check if user with this phone already exists
                self.user = User.objects.get(username=self.primary_phone)
            except User.DoesNotExist:
                # Create new user with phone as username
                # Default password: last 4 digits of CNIC or 'farmer1234'
                default_password = self.cnic[-4:] if self.cnic and len(self.cnic) >= 4 else 'farmer1234'
                self.user = User.objects.create_user(
                    username=self.primary_phone,
                    email=self.email if self.email else f'{self.primary_phone}@farmer.local',
                    password=default_password,
                    first_name=self.first_name,
                    last_name=self.last_name,
                    is_active=True
                )
                # Set farmer flag if exists
                if hasattr(self.user, 'is_farmer'):
                    self.user.is_farmer = True
                    self.user.save(update_fields=['is_farmer'])
        
        super().save(*args, **kwargs)
    
    def generate_unique_farmer_id(self):
        """Generate a simple sequential farmer ID like FM01, FM02, etc."""
        
        # Find the highest existing farmer ID with FM prefix
        existing_ids = Farmer.objects.filter(
            farmer_id__startswith='FM'
        ).values_list('farmer_id', flat=True)
        
        # Extract numbers from existing IDs and find the next sequential number
        numbers = []
        for farmer_id in existing_ids:
            # Extract number part after 'FM' prefix
            number_part = farmer_id[2:]  # Remove 'FM' prefix
            if number_part.isdigit():
                numbers.append(int(number_part))
        
        # Get next number (start from 1 if no existing IDs)
        next_number = max(numbers) + 1 if numbers else 1
        
        # Format: FM + 2-digit sequential number (FM01, FM02, etc.)
        return f"FM{next_number:02d}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None


class FarmingHistory(models.Model):
    """Model to track detailed farming history for each farmer"""
    
    SEASON_CHOICES = [
        ('kharif', _('Kharif (Summer)')),
        ('rabi', _('Rabi (Winter)')),
        ('zaid', _('Zaid (Spring)')),
    ]
    
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='history_records', verbose_name=_('Farmer'))
    year = models.PositiveIntegerField(verbose_name=_('Year'))
    season = models.CharField(max_length=10, choices=SEASON_CHOICES, verbose_name=_('Season'))
    crop_name = models.CharField(max_length=100, verbose_name=_('Crop Name'))
    area_cultivated = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_('Area Cultivated (acres)'))
    total_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_('Total Yield (kg)'))
    yield_per_acre = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_('Yield per Acre (kg)'))
    input_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_('Input Cost'))
    market_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_('Market Price per kg'))
    total_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_('Total Income'))
    profit_loss = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name=_('Profit/Loss'))
    farming_practices_used = models.TextField(blank=True, verbose_name=_('Farming Practices Used'))
    challenges_faced = models.TextField(blank=True, verbose_name=_('Challenges Faced'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Farming History')
        verbose_name_plural = _('Farming Histories')
        unique_together = ['farmer', 'year', 'season', 'crop_name']
        ordering = ['-year', '-created_at']
    
    def __str__(self):
        return f"{self.farmer.full_name} - {self.crop_name} ({self.season} {self.year})"
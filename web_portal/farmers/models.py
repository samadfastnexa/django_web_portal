from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Farmer(models.Model):
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
    
    FARM_OWNERSHIP_CHOICES = [
        ('owned', _('Owned')),
        ('leased', _('Leased')),
        ('shared', _('Shared/Partnership')),
        ('tenant', _('Tenant Farming')),
    ]
    
    FARMING_EXPERIENCE_CHOICES = [
        ('beginner', _('0-2 years')),
        ('intermediate', _('3-10 years')),
        ('experienced', _('11-20 years')),
        ('expert', _('20+ years')),
    ]
    
    # Personal Information
    farmer_id = models.CharField(max_length=20, unique=True, verbose_name=_('Farmer ID'))
    first_name = models.CharField(max_length=50, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=50, verbose_name=_('Last Name'))
    name = models.CharField(max_length=100, verbose_name=_('Full Name'))  # Keep for backward compatibility
    father_name = models.CharField(max_length=100, blank=True, verbose_name=_('Father Name'))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date of Birth'))
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name=_('Gender'))
    national_id = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name=_('National ID/CNIC'))
    
    # Contact Information
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    primary_phone = models.CharField(validators=[phone_regex], max_length=17, verbose_name=_('Primary Phone'))
    secondary_phone = models.CharField(validators=[phone_regex], max_length=17, blank=True, verbose_name=_('Secondary Phone'))
    email = models.EmailField(blank=True, verbose_name=_('Email Address'))
    
    # Address Information
    address = models.TextField(verbose_name=_('Complete Address'))
    village = models.CharField(max_length=100, verbose_name=_('Village'))
    tehsil = models.CharField(max_length=100, verbose_name=_('Tehsil'))
    district = models.CharField(max_length=100, verbose_name=_('District'))
    province = models.CharField(max_length=100, verbose_name=_('Province/State'))
    postal_code = models.CharField(max_length=10, blank=True, verbose_name=_('Postal Code'))
    
    # Location coordinates (existing fields)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_('Current Latitude'))
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_('Current Longitude'))
    farm_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_('Farm Latitude'))
    farm_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name=_('Farm Longitude'))
    
    # Education and Background
    education_level = models.CharField(max_length=20, choices=EDUCATION_CHOICES, default='primary', verbose_name=_('Education Level'))
    occupation_besides_farming = models.CharField(max_length=200, blank=True, verbose_name=_('Other Occupation'))
    
    # Farm Ownership and Details
    total_land_area = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text=_('Total land area in acres'), verbose_name=_('Total Land Area (acres)'))
    cultivated_area = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text=_('Currently cultivated area in acres'), verbose_name=_('Cultivated Area (acres)'))
    farm_ownership_type = models.CharField(max_length=20, choices=FARM_OWNERSHIP_CHOICES, verbose_name=_('Farm Ownership Type'))
    land_documents = models.TextField(blank=True, help_text=_('Details about land ownership documents'), verbose_name=_('Land Documents'))
    
    # Farming Experience and History
    farming_experience = models.CharField(max_length=20, choices=FARMING_EXPERIENCE_CHOICES, verbose_name=_('Farming Experience'))
    years_of_farming = models.PositiveIntegerField(default=0, verbose_name=_('Years of Farming'))
    main_crops_grown = models.TextField(help_text=_('List of main crops grown by the farmer'), verbose_name=_('Main Crops Grown'))
    farming_methods = models.TextField(blank=True, help_text=_('Traditional, modern, organic, etc.'), verbose_name=_('Farming Methods'))
    irrigation_source = models.CharField(max_length=200, blank=True, verbose_name=_('Irrigation Source'))
    
    # Financial Information
    annual_income_range = models.CharField(max_length=100, blank=True, verbose_name=_('Annual Income Range'))
    bank_account_details = models.TextField(blank=True, verbose_name=_('Bank Account Details'))
    
    # Family Information
    family_members_count = models.PositiveIntegerField(default=1, verbose_name=_('Family Members Count'))
    dependents_count = models.PositiveIntegerField(default=0, verbose_name=_('Dependents Count'))
    family_involved_in_farming = models.BooleanField(default=False, verbose_name=_('Family Involved in Farming'))
    
    # Registration and Status
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name=_('Registration Date'))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_('Last Updated'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_verified = models.BooleanField(default=False, verbose_name=_('Is Verified'))
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_farmers', verbose_name=_('Registered By'))
    
    # Additional Notes
    notes = models.TextField(blank=True, verbose_name=_('Additional Notes'))
    profile_picture = models.ImageField(upload_to='farmer_profiles/', null=True, blank=True, verbose_name=_('Profile Picture'))
    
    class Meta:
        verbose_name = _('Farmer')
        verbose_name_plural = _('Farmers')
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['farmer_id']),
            models.Index(fields=['district', 'tehsil']),
            models.Index(fields=['registration_date']),
            models.Index(fields=['is_active', 'is_verified']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.farmer_id})"
    
    def save(self, *args, **kwargs):
        # Auto-generate full name from first and last name
        self.name = f"{self.first_name} {self.last_name}"
        
        # Auto-generate farmer_id if not provided
        if not self.farmer_id:
            self.farmer_id = self.generate_unique_farmer_id()
        
        super().save(*args, **kwargs)
    
    def generate_unique_farmer_id(self):
        """Generate a unique farmer ID based on district and sequential number"""
        import re
        from datetime import datetime
        
        # Clean district name for ID generation
        district_clean = re.sub(r'[^a-zA-Z]', '', self.district.upper())[:3] if self.district else 'GEN'
        
        # Get current year
        current_year = datetime.now().year
        
        # Find the highest existing farmer ID for this district and year
        prefix = f"{district_clean}{current_year}"
        existing_ids = Farmer.objects.filter(
            farmer_id__startswith=prefix
        ).values_list('farmer_id', flat=True)
        
        # Extract numbers from existing IDs and find the next sequential number
        numbers = []
        for farmer_id in existing_ids:
            # Extract number part after prefix
            number_part = farmer_id[len(prefix):]
            if number_part.isdigit():
                numbers.append(int(number_part))
        
        # Get next number (start from 1 if no existing IDs)
        next_number = max(numbers) + 1 if numbers else 1
        
        # Format: DISTRICT_CODE + YEAR + 4-digit sequential number
        return f"{prefix}{next_number:04d}"
    
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
    
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='farming_history', verbose_name=_('Farmer'))
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
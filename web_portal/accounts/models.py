from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Permission
from django.core.validators import FileExtensionValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
# Import models from FieldAdvisoryService
from FieldAdvisoryService.models import Region, Zone, Territory
# ✅ Image size validator
def validate_image_size(image):
    max_size_mb = 2
    # Handle cases where file might not exist yet or is being updated
    try:
        if hasattr(image, 'size') and image.size:
            if image.size > max_size_mb * 1024 * 1024:
                raise ValidationError(f"Image file too large ( > {max_size_mb}MB )")
    except (OSError, FileNotFoundError):
        # File doesn't exist yet or path issue - skip validation
        pass

# ✅ Role Model
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    # permissions = models.ManyToManyField(Permission, related_name='roles')
    def __str__(self):
        return self.name
class Designation(models.TextChoices):
    CEO = "CEO", "CEO – Orange Protection"
    NSM = "NSM", "National Sales Manager"

    RSL = "RSL", "Regional Sales Leader"
    DRSL = "DRSL", "Deputy Regional Sales Leader"

    ZM = "ZM", "Zonal Manager"
    DPL = "DPL", "Deputy Product Leader"

    SR_PL = "SR_PL", "Senior Product Leader"
    PL = "PL", "Product Leader"
    SR_FSM = "SR_FSM", "Senior Farmer Service Manager"
    FSM = "FSM", "Farmer Service Manager"

    SR_MTO = "SR_MTO", "Senior MTO"
    MTO = "MTO", "MTO"
    
# ✅ Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        if not extra_fields.get('username'):
            raise ValueError("Username is required.")
        if not extra_fields.get('first_name'):
            raise ValueError("First name is required.")
        if not extra_fields.get('last_name'):
            raise ValueError("Last name is required.")
        # if not extra_fields.get('profile_image'):
        #     raise ValueError("Profile image is required.")

        email = self.normalize_email(email)

        # Default inactive for normal users
        extra_fields.setdefault('is_active', False)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        # Default role: FirstRole
        if 'role' not in extra_fields or not extra_fields['role']:
            try:
                default_role = Role.objects.get(name="FirstRole")
            except Role.DoesNotExist:
                raise ValueError("Role 'FirstRole' does not exist.")
            extra_fields['role'] = default_role

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Set required superuser flags
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        # Default role: Admin
        if 'role' not in extra_fields or not extra_fields['role']:
            try:
                admin_role = Role.objects.get(name="Admin")
            except Role.DoesNotExist:
                raise ValueError("Role 'Admin' does not exist.")
            extra_fields['role'] = admin_role

        return self.create_user(email, password, **extra_fields)

# ✅ Custom User Model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[RegexValidator(r'^[\w.@+-]+$', 'Enter a valid username.')]
    )

    first_name = models.CharField(
        max_length=150,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters are allowed.')]
    )

    last_name = models.CharField(
        max_length=150,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters are allowed.')]
    )

    profile_image = models.ImageField(
        upload_to='profile_images/',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png']), # ✅ Format check
            validate_image_size,                            # ✅ Size check
        ]
    )

    date_joined = models.DateTimeField(default=timezone.now)

    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=False)
    
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_sales_staff = models.BooleanField(default=False)  # ✅ New field
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email

class SalesStaffProfile(models.Model):
# link to User via AUTH_USER_MODEL to avoid import timing issues
    user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='sales_profile' , # ✅ must match the serializer field
    null=True,  # ✅ allow no user if vacant
    blank=True
)
    # employee_code = models.CharField(max_length=50)
    employee_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    # designation = models.CharField(max_length=100)
    designation = models.CharField(
        max_length=50,
        choices=Designation.choices
    )
    # use lazy app.model strings to avoid circular import
#     company = models.ForeignKey(
#     'FieldAdvisoryService.Company',
#     on_delete=models.SET_NULL,
#     null=True,
#     blank=True
# )
#     region = models.ForeignKey('FieldAdvisoryService.Region', on_delete=models.SET_NULL, null=True, blank=True)
#     zone = models.ForeignKey('FieldAdvisoryService.Zone', on_delete=models.SET_NULL, null=True, blank=True)
#     territory = models.ForeignKey('FieldAdvisoryService.Territory', on_delete=models.SET_NULL, null=True, blank=True)
  
  # ✅ Many-to-Many instead of ForeignKey
    companies   = models.ManyToManyField('FieldAdvisoryService.Company', blank=True, related_name="sales_profiles")
    regions     = models.ManyToManyField('FieldAdvisoryService.Region', blank=True, related_name="sales_profiles")
    zones       = models.ManyToManyField('FieldAdvisoryService.Zone', blank=True, related_name="sales_profiles")
    territories = models.ManyToManyField('FieldAdvisoryService.Territory', blank=True, related_name="sales_profiles")
    
    hod = models.ForeignKey('self', related_name='sales_hod', on_delete=models.SET_NULL, null=True, blank=True)
    master_hod = models.ForeignKey('self', related_name='sales_master_hod', on_delete=models.SET_NULL, null=True, blank=True)
    is_vacant = models.BooleanField(default=False, help_text="Mark if this position is vacant")
     #  leave quota fields
    sick_leave_quota = models.PositiveIntegerField(default=0)
    casual_leave_quota = models.PositiveIntegerField(default=0)
    others_leave_quota = models.PositiveIntegerField(default=0)
    
    def clean(self):
        if self.is_vacant:
            return

        if self.user and getattr(self.user, 'is_sales_staff', False):
            # CEO / NSM → no geo validation
            if self.designation in [Designation.CEO, Designation.NSM]:
                return  

            # Regional Sales Leader → at least 1 region
            if self.designation == Designation.RSL:
                if not self.regions.exists():
                    raise ValidationError("Regional Sales Leader must have at least one region.")

            # Deputy RSL / Zonal Manager → at least 1 zone
            elif self.designation in [Designation.DRSL, Designation.ZM]:
                if not self.zones.exists():
                    raise ValidationError("Zonal-level staff must have at least one zone.")

            # Territory-level staff
            elif self.designation in [
                Designation.PL, Designation.SR_PL, Designation.FSM,
                Designation.SR_FSM, Designation.DPL,
                Designation.MTO, Designation.SR_MTO
            ]:
                if not self.territories.exists():
                    raise ValidationError("Territory-level staff must have at least one territory.")

    def save(self, *args, **kwargs):
        # 1. Run validation first
        self.full_clean()

        # 2. Update linked user
        if self.user:
            if self.is_vacant:
                # If the slot is vacant, ensure user is NOT marked as sales staff
                if self.user.is_sales_staff:
                    self.user.is_sales_staff = False
                    self.user.save(update_fields=["is_sales_staff"])
            else:
                # If active, ensure user IS marked as sales staff
                if not self.user.is_sales_staff:
                    self.user.is_sales_staff = True
                    self.user.save(update_fields=["is_sales_staff"])

        # 3. Save profile
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # If linked user exists, unmark them as sales staff
        if self.user and self.user.is_sales_staff:
            self.user.is_sales_staff = False
            self.user.save(update_fields=["is_sales_staff"])

        super().delete(*args, **kwargs)

    def __str__(self):
        if self.is_vacant:
            return f"Vacant ({self.get_designation_display()})"
        elif self.user:
            return f"{self.user.email} ({self.get_designation_display()})"
        return f"Unassigned ({self.get_designation_display()})"
    

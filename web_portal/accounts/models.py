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
    
    class Meta:
        db_table = 'accounts_role'
        permissions = [
            ('manage_roles', 'Can manage roles and permissions'),
        ]
    
    def __str__(self):
        return self.name


# ✅ Dynamic Designation Model (replaces static TextChoices)
class DesignationModel(models.Model):
    """
    Dynamic designation/job title model.
    Allows adding new designations via admin without code changes.
    """
    code = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Short code (e.g., CEO, RSL, FSM)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Full designation name (e.g., Chief Executive Officer)"
    )
    level = models.IntegerField(
        default=0,
        help_text="Hierarchy level (0=highest, 10=lowest). Used for sorting."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive designations won't appear in dropdowns"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of role responsibilities"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_designationmodel'
        ordering = ['level', 'name']
        verbose_name = "Designation"
        verbose_name_plural = "Designations"
    
    def __str__(self):
        return f"{self.code} - {self.name}"


# Keep old TextChoices for backward compatibility during migration
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
    is_sales_staff = models.BooleanField(default=False)  # ✅ Sales staff flag
    is_dealer = models.BooleanField(default=False)  # ✅ Dealer flag
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'accounts_user'
        permissions = [
            ('manage_users', 'Can add/edit users'),
            ('view_user_reports', 'Can view user reports'),
            ('view_organogram', 'Can view organization hierarchy/organogram'),
        ]

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
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # ✅ Dynamic designation (ForeignKey to DesignationModel)
    designation = models.ForeignKey(
        DesignationModel,
        on_delete=models.PROTECT,
        related_name='staff_members',
        help_text="Job title/designation"
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
    
    # ==================== REPORTING HIERARCHY ====================
    # Self-referencing FK for manager-subordinate relationships
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        help_text="Direct manager/supervisor of this staff member"
    )
    
    hod = models.ForeignKey('self', related_name='sales_hod', on_delete=models.SET_NULL, null=True, blank=True)
    master_hod = models.ForeignKey('self', related_name='sales_master_hod', on_delete=models.SET_NULL, null=True, blank=True)
    is_vacant = models.BooleanField(default=False, help_text="Mark if this position is vacant")
     #  leave quota fields
    sick_leave_quota = models.PositiveIntegerField(default=0)
    casual_leave_quota = models.PositiveIntegerField(default=0)
    others_leave_quota = models.PositiveIntegerField(default=0)
    
    # ==================== REPORTING HIERARCHY METHODS ====================
    
    def get_all_subordinates(self, include_self=False):
        """
        Recursively get all subordinates (direct + indirect) in the reporting chain.
        
        Args:
            include_self (bool): Whether to include this staff member in the result
            
        Returns:
            QuerySet: All subordinates under this manager
        """
        from django.db.models import Q
        
        subordinate_ids = set()
        if include_self:
            subordinate_ids.add(self.id)
        
        def _collect_subordinates(manager_id):
            # Get direct subordinates
            direct_subs = SalesStaffProfile.objects.filter(
                manager_id=manager_id,
                is_vacant=False
            ).values_list('id', flat=True)
            
            for sub_id in direct_subs:
                if sub_id not in subordinate_ids:
                    subordinate_ids.add(sub_id)
                    # Recursively get their subordinates
                    _collect_subordinates(sub_id)
        
        _collect_subordinates(self.id)
        return SalesStaffProfile.objects.filter(id__in=subordinate_ids)
    
    def get_reporting_chain(self, include_self=True):
        """
        Get the upward reporting chain (manager → manager's manager → ... → CEO).
        
        Args:
            include_self (bool): Whether to include this staff member in the chain
            
        Returns:
            list: Ordered list of SalesStaffProfile objects from self to top-level manager
        """
        chain = []
        if include_self:
            chain.append(self)
        
        current = self.manager
        max_depth = 20  # Prevent infinite loops
        depth = 0
        
        while current and depth < max_depth:
            chain.append(current)
            current = current.manager
            depth += 1
        
        return chain
    
    def is_subordinate_of(self, potential_manager):
        """
        Check if this staff member is a subordinate (direct or indirect) of another staff member.
        
        Args:
            potential_manager (SalesStaffProfile): The staff member to check against
            
        Returns:
            bool: True if this person reports to potential_manager in the hierarchy
        """
        if not potential_manager:
            return False
        
        reporting_chain = self.get_reporting_chain(include_self=False)
        return potential_manager in reporting_chain
    
    def get_subordinate_users(self):
        """
        Get all User objects of subordinates (useful for filtering data access).
        
        Returns:
            QuerySet: User objects of all subordinates
        """
        subordinates = self.get_all_subordinates(include_self=False)
        user_ids = subordinates.values_list('user_id', flat=True)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(id__in=user_ids)
    
    def get_subordinate_territory_ids(self):
        """
        Get all territory IDs assigned to subordinates (for data filtering).
        
        Returns:
            set: Set of territory IDs
        """
        subordinates = self.get_all_subordinates(include_self=False)
        territory_ids = set()
        
        for sub in subordinates:
            territory_ids.update(sub.territories.values_list('id', flat=True))
        
        return territory_ids
    
    def __str__(self):
        if self.user:
            return f"{self.user.get_full_name()} ({self.designation})"
        return f"Vacant - {self.designation}"
    
    def clean(self):
        if self.is_vacant:
            return

        if self.user and getattr(self.user, 'is_sales_staff', False):
            # Get designation code for comparison
            designation_code = self.designation.code if self.designation else None
            
            # CEO / NSM → no geo validation
            if designation_code in ['CEO', 'NSM']:
                return  

            # Note: M2M field validation (regions, zones, territories) is handled in admin.py
            # because M2M fields aren't available during model.clean()

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
    
    class Meta:
        db_table = 'accounts_salesstaffprofile'
        permissions = [
            ('manage_sales_staff', 'Can manage sales staff profiles'),
            ('view_hierarchy', 'Can view reporting hierarchy'),
            ('manage_hierarchy', 'Can assign/change managers'),
            ('view_subordinate_data', 'Can view subordinates data'),
            ('view_all_hierarchy', 'Can view entire organization hierarchy'),
        ]

    def __str__(self):
        designation_text = self.designation.name if self.designation else "No Designation"
        if self.is_vacant:
            return f"Vacant ({designation_text})"
        elif self.user:
            return f"{self.user.email} ({designation_text})"
        return f"Unassigned ({designation_text})"



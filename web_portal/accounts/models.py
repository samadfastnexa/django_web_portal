from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Permission
from django.core.validators import FileExtensionValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

# ✅ Image size validator
def validate_image_size(image):
    max_size_mb = 2
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Image file too large ( > {max_size_mb}MB )")

# ✅ Role Model
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return self.name

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
        if not extra_fields.get('profile_image'):
            raise ValueError("Profile image is required.")

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
            FileExtensionValidator(['jpg', 'jpeg', 'png']),
            validate_image_size,
        ]
    )

    date_joined = models.DateTimeField(default=timezone.now)

    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'profile_image']

    def __str__(self):
        return self.email

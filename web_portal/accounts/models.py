from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Permission
from django.core.validators import FileExtensionValidator, RegexValidator
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
# ✅ Custom Validator
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

# ✅ User Manager
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get('is_superuser'):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

# ✅ User Model
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[RegexValidator(r'^[\w.@+-]+$', 'Enter a valid username.')],
    )
    
    first_name = models.CharField(
        max_length=150,
        blank=True,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters are allowed.')]
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
        validators=[RegexValidator(r'^[A-Za-z\s]+$', 'Only letters are allowed.')]
    )

    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png']),
            validate_image_size,
        ]
    )
    date_joined = models.DateTimeField(default=timezone.now)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    


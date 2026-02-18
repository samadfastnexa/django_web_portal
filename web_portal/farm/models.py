# farm/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django_google_maps.fields import AddressField, GeoLocationField

User = get_user_model()

class Farm(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farms")
    address = AddressField(max_length=255)
    geolocation = GeoLocationField()  # latitude, longitude
    size = models.DecimalField(max_digits=10, decimal_places=2, help_text="Size in acres/hectares")
    soil_type = models.CharField(max_length=100, choices=[
        ("clay", "Clay"),
        ("sandy", "Sandy"),
        ("silty", "Silty"),
        ("peaty", "Peaty"),
        ("chalky", "Chalky"),
        ("loamy", "Loamy"),
    ])
    ownership_details = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Indicates if the farm is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp")

    class Meta:
        db_table = 'farm_farm'
        ordering = ['-created_at']

    def soft_delete(self):
        """Soft delete the farm by setting deleted_at timestamp and is_active to False"""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save()

    def restore(self):
        """Restore a soft deleted farm"""
        self.deleted_at = None
        self.is_active = True
        self.save()

    @property
    def is_deleted(self):
        """Check if the farm is soft deleted"""
        return self.deleted_at is not None

    def __str__(self):
        return f"{self.name} - {self.owner}"

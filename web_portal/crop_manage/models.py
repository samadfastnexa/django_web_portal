from django.db import models
from django.conf import settings


class Crop(models.Model):
    name = models.CharField(max_length=100)
    variety = models.CharField(max_length=100, blank=True, null=True)
    season = models.CharField(max_length=50, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.variety})" if self.variety else self.name


class CropStage(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="stages")
    stage_name = models.CharField(max_length=200)
    days_after_sowing = models.IntegerField()
    brand = models.CharField(max_length=200, blank=True, null=True)
    active_ingredient = models.CharField(max_length=200, blank=True, null=True)
    dose_per_acre = models.CharField(max_length=100, blank=True, null=True)
    purpose = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.crop.name} - {self.stage_name}"

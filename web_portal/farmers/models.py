from django.db import models

class Farmer(models.Model):
    name = models.CharField(max_length=100)

    # These fields will store coordinates
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    farm_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    farm_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.name
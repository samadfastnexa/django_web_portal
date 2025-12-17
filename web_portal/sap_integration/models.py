from django.db import models


class Policy(models.Model):
    """Stores policies derived from SAP Projects (UDF U_pol)."""
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    policy = models.CharField(max_length=255, blank=True, null=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Policy'
        verbose_name_plural = 'Policies'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.code} - {self.policy or 'N/A'}"

class HanaConnect(models.Model):
    class Meta:
        managed = False
        verbose_name = 'HANA Connect'
        verbose_name_plural = 'HANA Connect'

    def __str__(self):
        return 'HANA Connect'

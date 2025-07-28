from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSetting(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    slug = models.SlugField()
    color_theme = models.CharField(max_length=50, blank=True, null=True)
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=10, choices=[("en", "English"), ("ur", "Urdu")], default="en")
    company_timings = models.JSONField(default=list, blank=True)
    value = models.CharField(max_length=255)
    radius_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'slug')  # ✅ Ensures slug is unique per user or globally (user=None)

    def __str__(self):
        return f"{'Global' if self.user is None else self.user.username} - {self.slug}"

from django.contrib.auth import get_user_model
from django.db import models
import json

User = get_user_model()

class UserSetting(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    slug = models.SlugField(unique=True)
    color_theme = models.CharField(max_length=50, blank=True, null=True)
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=10, choices=[("en", "English"), ("ur", "Urdu")], default="en")

    # 🕒 Store company timings as serialized list ["09:00", "17:00"]
    company_timings = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('user', 'slug')

    def __str__(self):
        return f"{self.user.username if self.user else 'Global'} - {self.slug}"

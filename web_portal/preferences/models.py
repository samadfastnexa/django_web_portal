from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import json
User = get_user_model()
class Setting(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    slug = models.SlugField(unique=True)
    # value = models.TextField()  # JSON string of settings
    value = models.JSONField(default=dict)  # ✅ Must be JSONField

    # ✅ Add these fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        db_table = 'preferences_setting'
        unique_together = ('user', 'slug')

    def __str__(self):
        return f"{'Global' if self.user is None else self.user.username} - {self.slug}"

    def get_value(self):
        """
        Get the value. Since we're using JSONField, it's already a Python object.
        For backward compatibility, handle both JSONField (dict/list) and TextField (str) formats.
        """
        if isinstance(self.value, str):
            try:
                return json.loads(self.value)
            except (ValueError, TypeError):
                return self.value
        return self.value

    def set_value(self, data):
        """
        Set the value. Since we're using JSONField, just assign the Python object directly.
        JSONField handles serialization automatically.
        """
        # JSONField accepts dict, list, str, int, float, bool, None
        if not isinstance(data, (dict, list, str, int, float, bool, type(None))):
            raise ValidationError("Value must be JSON-serializable (dict, list, str, int, float, bool, or None).")
        self.value = data
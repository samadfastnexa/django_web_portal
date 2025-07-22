from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
import os
from datetime import datetime, timedelta
from django.utils import timezone
from preferences.models import UserSetting
# ✅ File size validator (already in your file)
def validate_file_size(value):
    limit = 2 * 1024 * 1024  # 2MB
    if value.size > limit:
        raise ValidationError("File size must be under 2MB.")

# ✅ ✅ Add this below the size validator
def validate_file_extension(value):
    valid_extensions = [
        '.png', '.jpg', '.jpeg', '.pdf',
        '.doc', '.docx', '.xls', '.xlsx'
    ]
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError("Unsupported file type.")

# ✅ Attendance Model
class Attendance(models.Model):
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_user'
    )
    attendee_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_marked_by'
    )
    check_in_time = models.DateTimeField()
    check_out_time = models.DateTimeField(blank=True, null=True)
    check_in_gap = models.DurationField(blank=True, null=True)
    check_out_gap = models.DurationField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    attachment = models.FileField(
        upload_to='attendance_attachments/',
        validators=[validate_file_size, validate_file_extension],
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attendance of {self.user_id.email} on {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        now = timezone.now()

        # Try to get user-specific setting or fallback to global
        try:
            setting = UserSetting.objects.get(user=self.user_id, slug="attendance-policy")
        except UserSetting.DoesNotExist:
            setting = UserSetting.objects.filter(user__isnull=True, slug="attendance-policy").first()

        # Default to 09:00-17:00 if not set
        company_timings = setting.company_timings if setting and setting.company_timings else {"start": "09:00", "end": "17:00"}

        try:
            company_start = datetime.strptime(company_timings["start"], "%H:%M").time()
            company_end = datetime.strptime(company_timings["end"], "%H:%M").time()
        except (KeyError, ValueError):
            company_start = datetime.strptime("09:00", "%H:%M").time()
            company_end = datetime.strptime("17:00", "%H:%M").time()

        # Calculate check-in gap (from official start time)
        if self.check_in_time:
            official_start = self.check_in_time.replace(hour=company_start.hour, minute=company_start.minute, second=0)
            self.check_in_gap = self.check_in_time - official_start

        # Calculate check-out gap (from official end time)
        if self.check_out_time:
            official_end = self.check_out_time.replace(hour=company_end.hour, minute=company_end.minute, second=0)
            self.check_out_gap = self.check_out_time - official_end

        super().save(*args, **kwargs)
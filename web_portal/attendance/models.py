from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import os

# ✅ File size validator
def validate_file_size(value):
    limit = 2 * 1024 * 1024  # 2MB
    if value.size > limit:
        raise ValidationError("File size must be under 2MB.")

# ✅ File extension validator
def validate_file_extension(value):
    valid_extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.docx', '.xls', '.xlsx']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError("Unsupported file type.")

# ✅ Attendance Model
class Attendance(models.Model):
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        db_column='user_id'
    )
    attendee_id = models.CharField(max_length=100)
    check_in_time = models.DateTimeField()
    check_out_time = models.DateTimeField(null=True, blank=True)
    check_in_gap = models.DurationField(null=True, blank=True)
    check_out_gap = models.DurationField(null=True, blank=True)
    location = models.CharField(max_length=255)
    attachment = models.FileField(
        upload_to='attendance_attachments/',
        validators=[validate_file_size, validate_file_extension],
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.check_in_time and not self.check_in_gap:
            self.check_in_gap = timezone.now() - self.check_in_time
        if self.check_out_time and self.check_in_time:
            self.check_out_gap = self.check_out_time - self.check_in_time
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user_id.username} - {self.check_in_time.date()}"

    class Meta:
        verbose_name = "Attendance"
        verbose_name_plural = "Attendances"

class AttendanceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    CHECK_TYPE_CHOICES = [
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_requests'
    )
    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.CASCADE,
        related_name='requests',
        db_column='attendance_id'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    check_type = models.CharField(max_length=10, choices=CHECK_TYPE_CHOICES)
    check_in_time = models.DateTimeField()
    check_out_time = models.DateTimeField()
    check_in_gap = models.DurationField()
    check_out_gap = models.DurationField()
    reason = models.TextField(null=False, blank=False)
    attachment = models.FileField(
        upload_to='attendance_request_attachments/',
        validators=[validate_file_size, validate_file_extension],
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def can_check_in(self):
        return self.status == 'approved' and self.check_type == 'check_in'

    def __str__(self):
        return f"Request by {self.user.email} - {self.status} - {self.check_type}"

    def save(self, *args, **kwargs):
        if self.check_in_time and not self.check_in_gap:
            self.check_in_gap = timezone.now() - self.check_in_time
        if self.check_out_time and self.check_in_time and not self.check_out_gap:
            self.check_out_gap = self.check_out_time - self.check_in_time
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Attendance Request"
        verbose_name_plural = "Attendance Requests"
        permissions = [
            ("approve_attendance_request", "Can approve/reject attendance requests"),
        ]

    

# ✅ Temporary Test Model (optional)
class TestAdminModel(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

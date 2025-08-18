from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, time, timedelta

from django.utils.timezone import localdate
# from .validators import validate_file_size, validate_file_extension

User = get_user_model()
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

class Attendance(models.Model):
    # Logged in user (marker)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_marked_by_me',
        db_column='user_id'
    )
    # Attendee
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_as_attendee',
        db_column='attendee_id'
    )

    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)

    check_in_gap = models.DurationField(null=True, blank=True)
    check_out_gap = models.DurationField(null=True, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    attachment = models.FileField(
        upload_to='attendance_attachments/',
        validators=[validate_file_size, validate_file_extension],
        null=True,
        blank=True
    )

    SOURCE_CHOICES = [('manual', 'Manual'), ('request', 'Request')]
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default="manual")

    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        now = timezone.now()

        # Require at least one time
        if not self.check_in_time and not self.check_out_time:
            raise ValidationError("At least one of check-in or check-out time must be set.")

        # No future times
        if self.check_in_time and self.check_in_time > now:
            raise ValidationError("Check-in time cannot be in the future.")
        if self.check_out_time and self.check_out_time > now:
            raise ValidationError("Check-out time cannot be in the future.")

        # Same day for in/out
        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                raise ValidationError("Check-out time cannot be before check-in time.")
            if self.check_in_time.date() != self.check_out_time.date():
                raise ValidationError("Check-in and check-out must be on the same day.")

        # Prevent multiple entries for same user on same date
        check_date = None
        if self.check_in_time:
            check_date = self.check_in_time.date()
        elif self.created_at:
            check_date = self.created_at.date()

        if check_date:
            existing = Attendance.objects.filter(
                attendee=self.attendee,
                created_at__date=check_date
            ).exclude(pk=self.pk).exists()
            if existing:
                raise ValidationError("Attendance for this user already exists today.")

    def save(self, *args, **kwargs):
        self.full_clean()

        # Office timings
        opening_time = time(9, 0)
        closing_time = time(18, 0)

        # Calculate check_in_gap
        if self.check_in_time:
            official_open = datetime.combine(
                self.check_in_time.date(),
                opening_time,
                tzinfo=self.check_in_time.tzinfo
            )
            self.check_in_gap = self.check_in_time - official_open

        # Calculate check_out_gap
        if self.check_out_time:
            official_close = datetime.combine(
                self.check_out_time.date(),
                closing_time,
                tzinfo=self.check_out_time.tzinfo
            )
            self.check_out_gap = self.check_out_time - official_close

        super().save(*args, **kwargs)

    def __str__(self):
        check_in_date = self.check_in_time.date() if self.check_in_time else "N/A"
        return f"{self.attendee.username} (marked by {self.user.username}) on {check_in_date}"
    
class AttendanceRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    CHECK_IN = 'check_in'
    CHECK_OUT = 'check_out'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    CHECK_TYPE_CHOICES = [
        (CHECK_IN, 'Check In'),
        (CHECK_OUT, 'Check Out'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_requests'
    )
    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='requests'
    )
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()  # run model-level validation
        is_approved_now = False

        # Detect approval change
        if self.pk:
            previous = AttendanceRequest.objects.filter(pk=self.pk).first()
            if (
                previous
                and previous.status != self.STATUS_APPROVED
                and self.status == self.STATUS_APPROVED
            ):
                is_approved_now = True
        elif self.status == self.STATUS_APPROVED:
            is_approved_now = True

        super().save(*args, **kwargs)

        # Handle attendance creation/update
        if is_approved_now:
            attendance_date = (
                self.check_in_time.date()
                if self.check_type == self.CHECK_IN and self.check_in_time
                else self.check_out_time.date()
                if self.check_out_time
                else timezone.now().date()
            )

            attendance, created = Attendance.objects.get_or_create(
                attendee=self.user,
                created_at__date=attendance_date,
                defaults={
                    "user": self.user,  # self-service (same person marking & attending)
                    "check_in_time": self.check_in_time if self.check_type == self.CHECK_IN else None,
                    "check_out_time": self.check_out_time if self.check_type == self.CHECK_OUT else None,
                    "source": "request",
                },
            )

            if not created:  # ✅ If already exists → update record
                if self.check_type == self.CHECK_IN and self.check_in_time:
                    attendance.check_in_time = self.check_in_time
                if self.check_type == self.CHECK_OUT and self.check_out_time:
                    attendance.check_out_time = self.check_out_time
                attendance.source = "request"
                attendance.save()

            # Link back to request
            if not self.attendance_id:
                self.attendance = attendance
                super().save(update_fields=["attendance"])

    def __str__(self):
        return f"{self.user.username} - {self.check_type} ({self.status})"
    
    def clean(self):
        now = timezone.now()

        # Ensure at least one time is set based on check_type
        if self.check_type == self.CHECK_IN and not self.check_in_time:
            raise ValidationError("Check-in time is required for a check-in request.")
        if self.check_type == self.CHECK_OUT and not self.check_out_time:
            raise ValidationError("Check-out time is required for a check-out request.")

        # No future times allowed
        if self.check_in_time and self.check_in_time > now:
            raise ValidationError("Check-in time cannot be in the future.")
        if self.check_out_time and self.check_out_time > now:
            raise ValidationError("Check-out time cannot be in the future.")

        # If both present, validate order & same-day
        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                raise ValidationError("Check-out time cannot be before check-in time.")
            if self.check_in_time.date() != self.check_out_time.date():
                raise ValidationError("Check-in and check-out must be on the same day.")
# # ✅ Temporary Test Model (optional)
# class TestAdminModel(models.Model):
#     name = models.CharField(max_length=100)

#     def __str__(self):
#         return self.name

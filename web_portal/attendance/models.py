from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
from datetime import datetime, time, timedelta
from django.utils.timezone import localdate
from django.contrib.auth import get_user_model
# from .services import mark_attendance
User = get_user_model()

# -------------------
# File Validators
# -------------------
def validate_file_size(value):
    limit = 2 * 1024 * 1024  # 2MB
    if value.size > limit:
        raise ValidationError("File size must be under 2MB.")

def validate_file_extension(value):
    valid_extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.docx', '.xls', '.xlsx']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError("Unsupported file type.")

# -------------------
# Holiday Model
# -------------------
class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.date})"

# -------------------
# Attendance Model
# -------------------
class Attendance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_marked_by_me'
    )
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_as_attendee'
    )
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    check_in_gap = models.DurationField(null=True, blank=True)
    check_out_gap = models.DurationField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    attachment = models.FileField(upload_to='attendance_attachments/',
                                  validators=[validate_file_size, validate_file_extension],
                                  null=True, blank=True)
    SOURCE_CHOICES = [('manual', 'Manual'), ('request', 'Request')]
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)
    _current_user = None  # Temporary holder for request.user

    def set_current_user(self, user):
        self._current_user = user

    def clean(self):
        now = timezone.now()
        user = getattr(self, '_current_user', None)

        if not self.check_in_time and not self.check_out_time:
            raise ValidationError("At least one of check-in or check-out time must be set.")

        if self.check_in_time and self.check_in_time > now:
            raise ValidationError("Check-in time cannot be in the future.")
        if self.check_out_time and self.check_out_time > now:
            raise ValidationError("Check-out time cannot be in the future.")

        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                raise ValidationError("Check-out cannot be before check-in.")
            if self.check_in_time.date() != self.check_out_time.date():
                raise ValidationError("Check-in/out must be on the same day.")

        # Role-based rules
        if user and not (user.is_staff or user.is_superuser):
            if self.attendee != user:
                raise ValidationError("You cannot mark attendance for other users.")
            today = timezone.localdate()
            if (self.check_in_time and self.check_in_time.date() != today) or \
               (self.check_out_time and self.check_out_time.date() != today):
                raise ValidationError("You can only mark attendance for today.")

        # Duplicate prevention
        record_date = self.check_in_time.date() if self.check_in_time else self.check_out_time.date()
        qs = Attendance.objects.filter(attendee=self.attendee).filter(
            check_in_time__date=record_date
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(f"Attendance for {record_date} already exists.")

    def save(self, *args, **kwargs):
        self.full_clean()
        opening_time = time(9, 0)
        closing_time = time(18, 0)
        if self.check_in_time:
            official_open = datetime.combine(self.check_in_time.date(), opening_time, tzinfo=self.check_in_time.tzinfo)
            self.check_in_gap = self.check_in_time - official_open
        if self.check_out_time:
            official_close = datetime.combine(self.check_out_time.date(), closing_time, tzinfo=self.check_out_time.tzinfo)
            self.check_out_gap = self.check_out_time - official_close
        super().save(*args, **kwargs)

    def __str__(self):
        date_str = self.check_in_time.date() if self.check_in_time else "N/A"
        return f"{self.attendee.username} on {date_str}"

# -------------------
# Attendance Request
# -------------------
class AttendanceRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    CHECK_IN = 'check_in'
    CHECK_OUT = 'check_out'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected')
    ]
    CHECK_TYPE_CHOICES = [(CHECK_IN, 'Check In'), (CHECK_OUT, 'Check Out')]
#   user is the person who submitted the request (the requester).
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_requests')
    # this points to the actual Attendance record that will be updated once approved.
    # attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, null=True, blank=True, related_name='requests')
    attendance = models.ForeignKey(
    Attendance,
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name="requests"
)
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        now = timezone.now()

        # ✅ Only validate times if request is still pending (user submission)
        if self.status == self.STATUS_PENDING:
            if self.check_type == self.CHECK_IN and not self.check_in_time:
                raise ValidationError("Check-in time required.")
            if self.check_type == self.CHECK_OUT and not self.check_out_time:
                raise ValidationError("Check-out time required.")

        # ✅ Prevent future times (still useful even after approval)
        if self.check_in_time and self.check_in_time > now:
            raise ValidationError("Cannot set future check-in.")
        if self.check_out_time and self.check_out_time > now:
            raise ValidationError("Cannot set future check-out.")

        # ✅ Restrict normal users (not staff/superuser) to only today
        user = self.user
        if not (user.is_staff or user.is_superuser):
            today = timezone.localdate()
            if (self.check_in_time and self.check_in_time.date() != today) or \
            (self.check_out_time and self.check_out_time.date() != today):
                raise ValidationError("You can only request attendance for today.")
    
    

# -------------------
# Leave Request
# -------------------
class LeaveRequest(models.Model):
    TYPE_SICK = 'sick'
    TYPE_CASUAL = 'casual'
    TYPE_OTHER = 'other'

    LEAVE_CHOICES = [
        (TYPE_SICK, 'Sick'),
        (TYPE_CASUAL, 'Casual'),
        (TYPE_OTHER, 'Other')
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Validate dates
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

        # Check leave quota from sales profile
        profile = getattr(self.user, 'sales_profile', None)
        if profile and not (self.user.is_staff or self.user.is_superuser):
            leave_days = (self.end_date - self.start_date).days + 1
            quota_field = f"{self.leave_type}_leave_quota"
            remaining = getattr(profile, quota_field, 0)
            if leave_days > remaining:
                raise ValidationError(f"Insufficient {self.leave_type} leave quota. Remaining: {remaining} days.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

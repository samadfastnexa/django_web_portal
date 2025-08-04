from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import os
from django.contrib.auth import get_user_model
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

# ✅ Attendance Model
class Attendance(models.Model):
    
    # 1. User who is logged in (marker)
    user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='attendance_marked_by_me',
    db_column='user_id'  # optional
)

# 2. User whose attendance is marked (target user)
    attendee = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='attendance_as_attendee',
    db_column='attendee_id'  # optional
    )
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
    SOURCE_CHOICES = [('manual', 'Manual'), ('request', 'Request')]
    source = models.CharField(max_length=50, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.check_in_time and not self.check_in_gap:
            self.check_in_gap = timezone.now() - self.check_in_time
        if self.check_out_time and self.check_in_time:
            self.check_out_gap = self.check_out_time - self.check_in_time
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.attendee.username} (marked by {self.user.username}) on {self.check_in_time.date()}"


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

    # user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='attendance_requests')
    # attendance = models.ForeignKey('Attendance', on_delete=models.CASCADE, related_name='requests')
    # user = models.ForeignKey(  # requester
    #     settings.AUTH_USER_MODEL,
    #     on_delete=models.CASCADE,
    #     related_name='attendance_requests'
    # )
    # # 
    # attendance = models.ForeignKey(
    #     'Attendance',
    #     on_delete=models.CASCADE,
    #     related_name='requests',
    #     null=True,
    #     blank=True
    # )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_requests')
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, null=True, blank=True, related_name='requests')
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        is_approved_now = False

        if self.pk:
            previous = AttendanceRequest.objects.filter(pk=self.pk).first()
            if previous and previous.status != self.STATUS_APPROVED and self.status == self.STATUS_APPROVED:
                is_approved_now = True
        elif self.status == self.STATUS_APPROVED:
            is_approved_now = True

        super().save(*args, **kwargs)

        # ✅ Create or update Attendance on approval
        if is_approved_now:
            # Determine the attendance date
            attendance_date = (
                self.check_in_time.date()
                if self.check_type == self.CHECK_IN and self.check_in_time
                else self.check_out_time.date()
                if self.check_out_time
                else timezone.now().date()
            )

            # Try to find existing attendance for that user and day
            attendance = Attendance.objects.filter(
                user=self.user,
                created_at__date=attendance_date
            ).first()

            if not attendance:
                # Create new attendance
                attendance = Attendance.objects.create(
                    user=self.user,
                    attendee_id=str(self.user.id),
                    check_in_time=self.check_in_time if self.check_type == self.CHECK_IN else None,
                    check_out_time=self.check_out_time if self.check_type == self.CHECK_OUT else None,
                    location='Approved by admin',
                    source='request'
                )
            else:
                # Update existing attendance
                if self.check_type == self.CHECK_IN and self.check_in_time:
                    attendance.check_in_time = self.check_in_time
                if self.check_type == self.CHECK_OUT and self.check_out_time:
                    attendance.check_out_time = self.check_out_time
                attendance.source = 'request'
                attendance.save()

            # Link this attendance to the request
            if not self.attendance_id:
                self.attendance = attendance
                super().save(update_fields=['attendance'])
    

# ✅ Temporary Test Model (optional)
class TestAdminModel(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

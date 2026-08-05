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

    class Meta:
        db_table = 'attendance_holiday'

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
    check_in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    check_out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    check_in_image = models.ImageField(upload_to='attendance_checkin/',
                                       validators=[validate_file_size],
                                       null=True, blank=True)
    check_out_image = models.ImageField(upload_to='attendance_checkout/',
                                        validators=[validate_file_size],
                                        null=True, blank=True)
    # Removed attachment field - now using separate check_in_image and check_out_image
    SOURCE_CHOICES = [('manual', 'Manual'), ('request', 'Request')]
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default="manual")

    # Where the ATTENDEE works, stamped when the record is created from their
    # employee code (see FieldAdvisoryService.sap_geo). Recorded on the row
    # rather than looked up at read time so a report of last year's attendance
    # shows where people worked then, not where they work now.
    employee_code = models.CharField(
        max_length=50, blank=True, null=True, db_index=True,
        verbose_name="Employee code",
        help_text="Employee code the location below was resolved from",
    )
    # Text, not CharField: a national manager covers ~130 territories and these
    # list every one. That rules out a plain db_index too (MySQL cannot index
    # TEXT without a prefix length); `search=` still matches inside the list.
    region = models.TextField(
        blank=True, null=True, verbose_name="Region",
        help_text="Region(s) assigned to the attendee, comma separated.",
    )
    zone = models.TextField(
        blank=True, null=True, verbose_name="Zone",
        help_text="Zone(s) assigned to the attendee, comma separated.",
    )
    territory = models.TextField(
        blank=True, null=True, verbose_name="Territory",
        help_text="Territory/territories assigned to the attendee, comma separated.",
    )
    territory_code = models.IntegerField(
        blank=True, null=True, db_index=True,
        verbose_name="Territory code",
        help_text="SAP OTER.territryID, set only when the attendee has exactly one territory.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    _current_user = None  # Temporary holder for request.user

    class Meta:
        db_table = 'attendance_attendance'

    def set_current_user(self, user):
        self._current_user = user

    def clean(self):
        now = timezone.now()
        user = getattr(self, '_current_user', None)

        if not self.check_in_time and not self.check_out_time:
            raise ValidationError("At least one of check-in or check-out time must be set.")

        # Allow 5 minute tolerance for future time checks (handles clock skew and timezone issues)
        from datetime import timedelta
        tolerance = timedelta(minutes=5)
        
        # DEBUG: Log timezone comparison
        # if self.check_in_time:
        #     print(f"[ATTENDANCE DEBUG] Check-in time: {self.check_in_time}")
        #     print(f"[ATTENDANCE DEBUG] Server now: {now}")
        #     print(f"[ATTENDANCE DEBUG] Difference: {(self.check_in_time - now).total_seconds()} seconds")
        
        if self.check_in_time and self.check_in_time > (now + tolerance):
            raise ValidationError("Check-in time cannot be in the future.")
        if self.check_out_time and self.check_out_time > (now + tolerance):
            raise ValidationError("Check-out time cannot be in the future.")

        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                raise ValidationError("Check-out cannot be before check-in.")
            if timezone.localtime(self.check_in_time).date() != timezone.localtime(self.check_out_time).date():
                raise ValidationError("Check-in/out must be on the same day.")

        # Role-based rules
        if user and not (user.is_staff or user.is_superuser):
            if self.attendee != user:
                raise ValidationError("You cannot mark attendance for other users.")
            today = timezone.localdate()
            if (self.check_in_time and timezone.localtime(self.check_in_time).date() != today) or \
               (self.check_out_time and timezone.localtime(self.check_out_time).date() != today):
                raise ValidationError("You can only mark attendance for today.")

        # Duplicate prevention
        record_date = timezone.localtime(self.check_in_time).date() if self.check_in_time else timezone.localtime(self.check_out_time).date()
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
            local_check_in = timezone.localtime(self.check_in_time)
            official_open = timezone.make_aware(datetime.combine(local_check_in.date(), opening_time))
            self.check_in_gap = self.check_in_time - official_open
        if self.check_out_time:
            local_check_out = timezone.localtime(self.check_out_time)
            official_close = timezone.make_aware(datetime.combine(local_check_out.date(), closing_time))
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

    class Meta:
        db_table = 'attendance_attendancerequest'

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
            if (self.check_in_time and timezone.localtime(self.check_in_time).date() != today) or \
            (self.check_out_time and timezone.localtime(self.check_out_time).date() != today):
                raise ValidationError("You can only request attendance for today.")
    
    

# -------------------
# Leave Request
# -------------------
class LeaveType(models.Model):
    """An editable kind of leave (Sick, Casual, ...).

    Replaces the hardcoded choices that used to live on LeaveRequest, so new
    types can be added from the admin instead of requiring a code change.
    """
    #: Codes that predate this model and still have a dedicated quota column on
    #: SalesStaffProfile. Those columns remain part of the public user API, so
    #: they stay authoritative for these three unless a LeaveQuota row overrides
    #: them - see quota_for().
    LEGACY_QUOTA_FIELDS = {
        'sick': 'sick_leave_quota',
        'casual': 'casual_leave_quota',
        'other': 'others_leave_quota',
    }

    code = models.SlugField(
        max_length=20, unique=True,
        help_text="Stable identifier used by the API, e.g. 'sick'. Avoid renaming.",
    )
    name = models.CharField(max_length=50, help_text="Label shown to users, e.g. 'Sick'.")
    description = models.CharField(max_length=200, blank=True)
    default_quota = models.PositiveIntegerField(
        default=0,
        help_text="Days allowed when a staff member has no specific quota for this type.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'attendance_leavetype'
        ordering = ['sort_order', 'name']
        verbose_name = 'Leave type'
        verbose_name_plural = 'Leave types'

    def __str__(self):
        return self.name

    def quota_for(self, profile):
        """Days of this leave type available to a SalesStaffProfile.

        Order: an explicit LeaveQuota row, then the legacy per-type column on
        the profile (kept for the three original types so the existing user
        API keeps working), then this type's default.
        """
        if profile is None:
            return 0
        row = self.quotas.filter(profile=profile).first()
        if row is not None:
            return row.days
        legacy_field = self.LEGACY_QUOTA_FIELDS.get(self.code)
        if legacy_field:
            return getattr(profile, legacy_field, 0) or 0
        return self.default_quota


class LeaveQuota(models.Model):
    """Days of one leave type granted to one staff member."""
    profile = models.ForeignKey(
        'accounts.SalesStaffProfile', on_delete=models.CASCADE, related_name='leave_quotas',
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='quotas')
    days = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'attendance_leavequota'
        unique_together = ('profile', 'leave_type')
        verbose_name = 'Leave quota'
        verbose_name_plural = 'Leave quotas'

    def __str__(self):
        return f'{self.profile} - {self.leave_type}: {self.days} day(s)'


class LeaveRequest(models.Model):
    TYPE_SICK = 'sick'
    TYPE_CASUAL = 'casual'
    TYPE_OTHER = 'other'

    #: Retained for the data migration and for callers that still map codes.
    #: The live list of types now comes from the LeaveType table.
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
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name='requests',
        help_text="Managed under Attendance > Leave types.",
    )
    start_date = models.DateField()
    # Optional clock times, so a half-day or part-day leave can say when it
    # actually runs. Left blank the request means the whole day, which is how
    # every existing row behaves.
    start_time = models.TimeField(
        null=True, blank=True,
        help_text="Optional. Leave blank for a full day.",
    )
    end_date = models.DateField()
    end_time = models.TimeField(
        null=True, blank=True,
        help_text="Optional. Leave blank for a full day.",
    )
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_leaverequest'

    def clean(self):
        # Validate dates
        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

        # Within a single day the clock times must also run forwards. Across
        # multiple days they cannot conflict, so they are not compared.
        if (
            self.start_date == self.end_date
            and self.start_time and self.end_time
            and self.end_time <= self.start_time
        ):
            raise ValidationError("End time must be after start time on a single-day leave.")

        # Check leave quota from sales profile
        profile = getattr(self.user, 'sales_profile', None)
        if profile and self.leave_type_id and not (self.user.is_staff or self.user.is_superuser):
            leave_days = (self.end_date - self.start_date).days + 1
            remaining = self.leave_type.quota_for(profile)
            if leave_days > remaining:
                raise ValidationError(
                    f"Insufficient {self.leave_type} leave quota. Remaining: {remaining} days."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

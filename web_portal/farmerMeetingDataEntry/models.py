from django.db import models
import uuid
import os
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings  # to access AUTH_USER_MODEL
import uuid
import os
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from FieldAdvisoryService.models import Region,Zone,Territory,Company
class Meeting(models.Model):
    id = models.CharField(
        max_length=20,
        primary_key=True,
        unique=True,
        editable=False
    )
    fsm_name = models.CharField(max_length=100, default="Unknown FSM")
    
    # Foreign Key relationships
    company_fk = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings_company')
    region_fk = models.ForeignKey(Region,on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings_region')
    zone_fk   = models.ForeignKey(Zone,on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings_zone')
    territory_fk = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings_territory')
    
    date = models.DateTimeField()
    location = models.CharField(max_length=200, default="Not specified", blank=True)
    total_attendees = models.PositiveIntegerField(default=0)
    key_topics_discussed = models.TextField(default="Not specified")
    products_discussed = models.TextField(blank=True, null=True, help_text="Products discussed during the meeting")
    presence_of_zm = models.BooleanField(default=False)
    presence_of_rsm = models.BooleanField(default=False)
    feedback_from_attendees = models.TextField(blank=True, null=True)
    suggestions_for_future = models.TextField(blank=True, null=True)
  
    # ✅ Soft delete flag
    is_active = models.BooleanField(default=True)
  
    # ✅ This is your user_id foreign key field
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='user_id',  # Optional, keeps DB column name as `user_id` 
        related_name='user_meetings'
    )

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"FM{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.user_id.username if self.user_id else 'No User'}"
    
    class Meta:
        db_table = 'farmermeetingdataentry_meeting'
        ordering = ['-id']
        verbose_name = "Farmer Advisory Meeting"
        verbose_name_plural = "Farmer Advisory Meetings"

class FarmerAttendance(models.Model):
    meeting = models.ForeignKey(Meeting, related_name='attendees', on_delete=models.CASCADE)
    
    # Link to farmer record (optional)
    farmer = models.ForeignKey('farmers.Farmer', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='meeting_attendances', 
                              help_text="Link to farmer record")
    
    farmer_name = models.CharField(max_length=100, blank=True,
                                  help_text="Farmer name (auto-filled from farmer record if linked)")
    contact_number = models.CharField(max_length=15, blank=True,
                                     help_text="Contact number (auto-filled from farmer record if linked)")
    acreage = models.FloatField(default=0.0)
    crop = models.CharField(max_length=100)

    def __str__(self):
        return self.farmer_name

    class Meta:
        db_table = 'farmer_meeting_attendees'  # 👈 custom table name

def validate_file_size(value):
    limit = 2 * 1024 * 1024  # 2 MB
    if value.size > limit:
        raise ValidationError("File size must be less than 2 MB.")

def validate_file_extension(value):
    valid_mime_types = [
        'image/png', 'image/jpeg',
        'application/pdf',
        'application/msword',  # .doc
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/vnd.ms-excel',  # .xls
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    ]
    ext = value.file.content_type
    if ext not in valid_mime_types:
        raise ValidationError("Unsupported file type.")

def upload_to_meeting(instance, filename):
    return f"meeting_uploads/{filename}"

class MeetingAttachment(models.Model):
    meeting = models.ForeignKey(Meeting, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=upload_to_meeting,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'xls', 'xlsx']
            ),
            validate_file_size,
        ]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'farmermeetingdataentry_meetingattachment'

    def __str__(self):
        return os.path.basename(self.file.name)

    def delete(self, *args, **kwargs):
        """Delete the model instance and its file if it exists"""
        # Try to delete the file, but don't fail if it doesn't exist
        try:
            if self.file and os.path.exists(self.file.path):
                self.file.delete(save=False)
        except Exception:
            pass  # File doesn't exist or can't be deleted, continue anyway
        super().delete(*args, **kwargs)
    
# field day 
class FieldDay(models.Model):
    id = models.CharField(max_length=20, primary_key=True, editable=False)
    title = models.CharField(max_length=200, verbose_name="Name of FSM", help_text="Enter the name of the Field Service Manager (FSM)")
    
    # Foreign Key relationships
    company_fk = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='field_days_company'
    )
    region_fk = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='field_days_region'
    )
    zone_fk = models.ForeignKey(
        Zone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='field_days_zone'
    )
    territory_fk = models.ForeignKey(
        Territory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='field_days_territory'
    )
    
    date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    total_participants = models.PositiveIntegerField(default=0, help_text="Total number of participants in the field day")
    demonstrations_conducted = models.PositiveIntegerField(default=0, help_text="Number of demonstrations conducted")
    feedback = models.TextField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="field_days")
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"FD{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.id} - {self.title}"
    
    class Meta:
        db_table = 'farmermeetingdataentry_fieldday'
        ordering = ['-id']
        verbose_name = "Field Day"
        verbose_name_plural = "Field Days"

class FieldDayAttendance(models.Model):
    field_day = models.ForeignKey(FieldDay, related_name="attendees", on_delete=models.CASCADE)
    
    # ✅ Link to farmer record (optional)
    farmer = models.ForeignKey('farmers.Farmer', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='field_day_attendances', 
                              verbose_name="Farmer",
                              help_text="Link to farmer record")
    
    # ✅ Attendee information (auto-filled from farmer if linked)
    farmer_name = models.CharField(max_length=100, blank=True,
                                  verbose_name="Farmer Name",
                                  help_text="Farmer name (auto-filled from farmer record if linked)")
    contact_number = models.CharField(max_length=15, blank=True,
                                     verbose_name="Contact Number",
                                     help_text="Contact number (auto-filled from farmer record if linked)")
    acreage = models.FloatField(default=0.0, 
                               verbose_name="Acreage",
                               help_text="Acreage for this specific field day")
    crop = models.CharField(max_length=100, blank=True, 
                          verbose_name="Crop",
                          help_text="Crop discussed/demonstrated (deprecated - use crops relationship)")
    
    class Meta:
        db_table = 'farmermeetingdataentry_fielddayattendance'


class FieldDayAttendanceCrop(models.Model):
    """Model to handle multiple crops per field day attendance"""
    attendance = models.ForeignKey(FieldDayAttendance, related_name="crops", on_delete=models.CASCADE)
    crop_name = models.CharField(max_length=100, help_text="Name of the crop")
    acreage = models.FloatField(default=0.0, help_text="Acreage for this specific crop")
    
    class Meta:
        unique_together = ['attendance', 'crop_name']  # Prevent duplicate crops for same attendance
        db_table = 'field_day_attendance_crops'
    
    def __str__(self):
        return f"{self.attendance.farmer_name} - {self.crop_name} ({self.acreage} acres)"
    
    def save(self, *args, **kwargs):
        # No special logic needed for FieldDayAttendanceCrop
        super().save(*args, **kwargs)

def upload_to_field_day(instance, filename):
    return f"field_day_uploads/{filename}"

class FieldDayAttachment(models.Model):
    field_day = models.ForeignKey(FieldDay, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=upload_to_field_day,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'xls', 'xlsx']
            ),
            validate_file_size,
        ]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return os.path.basename(self.file.name)

    class Meta:
        db_table = 'farmermeetingdataentry_fielddayattachment'

    def delete(self, *args, **kwargs):
        """Delete the model instance and its file if it exists"""
        # Try to delete the file, but don't fail if it doesn't exist
        try:
            if self.file and os.path.exists(self.file.path):
                self.file.delete(save=False)
        except Exception:
            pass  # File doesn't exist or can't be deleted, continue anyway
        super().delete(*args, **kwargs)


class HPMRequisition(models.Model):
    """High Profile Meeting requisition - approved BEFORE the meeting is arranged.

    Digitises the paper form "HIGH-PROFILE FARMER MEETING FOR GM/BM - REQUISITION
    FORM". Unlike Meeting / FieldDay (which record a meeting that already
    happened) this is a request: a senior manager submits it and an authorised
    approver (the CEO on the paper form) approves or rejects it with remarks.

    Who may submit and who may approve is NOT tied to a designation code - the
    right to decide is the grantable `approve_hpmrequisition` permission, so the
    hierarchy can change without touching this model.
    """

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    id = models.CharField(max_length=20, primary_key=True, unique=True, editable=False)

    # --- Requisition header -------------------------------------------------
    requisition_date = models.DateField(
        help_text="Date the requisition was raised (the form's 'Requisition Date').",
    )
    # The form's "GM/BM Name" - taken from whoever submitted, never typed, so the
    # printed name always matches the signature block.
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hpm_requisitions',
        help_text="Manager who raised this requisition (prints as GM/BM Name).",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    # --- HPM meeting details ----------------------------------------------
    company_fk = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hpm_requisitions_company',
    )
    region_fk = models.ForeignKey(
        Region, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hpm_requisitions_region',
    )
    zone_fk = models.ForeignKey(
        Zone, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hpm_requisitions_zone',
    )
    territory_fk = models.ForeignKey(
        Territory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hpm_requisitions_territory',
    )
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hpm_responsible_for',
        help_text="Staff member accountable for arranging the meeting.",
    )
    # Date AND time: a high-profile meeting has a start time, and this matches
    # Meeting.date / FieldDay.date, which are both DateTimeFields.
    meeting_date = models.DateTimeField(help_text="Date and start time of the meeting.")
    meeting_location = models.CharField(max_length=200)
    expected_attendees = models.PositiveIntegerField(
        default=0, help_text="No. of farmers / attendees expected.",
    )
    purpose = models.TextField(
        help_text="Purpose of meeting (product related campaign & sale commitment).",
    )
    remarks = models.TextField(blank=True)

    # --- Approval section --------------------------------------------------
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True,
    )
    ceo_remarks = models.TextField(
        blank=True, help_text="Approver's remarks; carries the reason on rejection.",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hpm_requisitions_reviewed',
        help_text="Who approved or rejected it (prints as CEO signature).",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lets a signal / caller detect the pending -> decided edge later.
        self._previous_status = self.status

    def save(self, *args, **kwargs):
        if not self.id:
            # Random suffix rather than "last + 1": the sequential scheme used by
            # MeetingSchedule races under concurrent inserts.
            self.id = f"HPM{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
        self._previous_status = self.status

    @property
    def is_decided(self):
        return self.status in (self.STATUS_APPROVED, self.STATUS_REJECTED)

    def __str__(self):
        who = self.submitted_by.get_username() if self.submitted_by else 'unknown'
        return f"{self.id} - {who} ({self.get_status_display()})"

    class Meta:
        db_table = 'farmermeetingdataentry_hpmrequisition'
        ordering = ['-id']
        verbose_name = 'HPM Requisition'
        verbose_name_plural = 'HPM Requisitions'
        indexes = [
            models.Index(fields=['status', 'requisition_date']),
            models.Index(fields=['submitted_by', 'status']),
        ]
        permissions = [
            ('approve_hpmrequisition', 'Can approve or reject HPM requisitions'),
        ]

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

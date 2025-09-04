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
from FieldAdvisoryService.serializers import Region,Zone,Territory
class Meeting(models.Model):
    id = models.CharField(
        max_length=20,
        primary_key=True,
        unique=True,
        editable=False
    )
    fsm_name = models.CharField(max_length=100, default="Unknown FSM")
    territory = models.CharField(max_length=100, default="Unknown Territory")
    zone = models.CharField(max_length=100, default="Unknown Zone")
    region = models.CharField(max_length=100, default="Unknown Region")
       # NEW – real FKs
    # company   = models.ForeignKey(Company,   on_delete=models.SET_NULL, null=True, blank=True)
    region_fk = models.ForeignKey(Region,on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings_region')
    zone_fk   = models.ForeignKey(Zone,on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings_zone')
    territory_fk = models.ForeignKey(Territory, on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings_territory')
    
    date = models.DateField()
    location = models.CharField(max_length=200, default="Not specified")
    total_attendees = models.PositiveIntegerField(default=0)
    key_topics_discussed = models.TextField(default="Not specified")
    presence_of_zm_rsm = models.BooleanField(default=False)
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

class FarmerAttendance(models.Model):
    meeting = models.ForeignKey(Meeting, related_name='attendees', on_delete=models.CASCADE)
    farmer_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
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

    def __str__(self):
        return os.path.basename(self.file.name)
    
# field day 
class FieldDay(models.Model):
    id = models.CharField(max_length=20, primary_key=True, editable=False)
    title = models.CharField(max_length=200)
    territory = models.CharField(max_length=100)
    zone = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    date = models.DateField()
    location = models.CharField(max_length=200)
    objectives = models.TextField(default="Not specified")
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default="draft", choices=[("draft","Draft"),("scheduled","Scheduled"),("completed","Completed")])
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="field_days")
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"FD{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

class FieldDayAttendance(models.Model):
    field_day = models.ForeignKey(FieldDay, related_name="attendees", on_delete=models.CASCADE)
    farmer_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    acreage = models.FloatField(default=0.0)
    crop = models.CharField(max_length=100)

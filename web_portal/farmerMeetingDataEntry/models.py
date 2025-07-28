from django.db import models
import uuid
import os
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings  # to access AUTH_USER_MODEL
import uuid
import os
from django.core.exceptions import ValidationError

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
    date = models.DateField()
    location = models.CharField(max_length=200, default="Not specified")
    total_attendees = models.PositiveIntegerField(default=0)
    key_topics_discussed = models.TextField(default="Not specified")
    presence_of_zm_rsm = models.BooleanField(default=False)
    feedback_from_attendees = models.TextField(blank=True, null=True)
    suggestions_for_future = models.TextField(blank=True, null=True)

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
        validators=[validate_file_size, validate_file_extension]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return os.path.basename(self.file.name)
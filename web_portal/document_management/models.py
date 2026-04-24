import os
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


def attachment_upload_path(instance, filename):
    """
    Generate upload path for attachments.
    Pattern: attachments/YYYY/MM/DD/filename
    """
    now = timezone.now()
    return os.path.join(
        'attachments',
        now.strftime('%Y'),
        now.strftime('%m'),
        now.strftime('%d'),
        filename
    )


def validate_file_size(file):
    """
    Validate file size (max 10MB by default).
    """
    max_size_mb = 10
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'File size cannot exceed {max_size_mb}MB.')


class Attachment(models.Model):
    """
    Model for storing document attachments.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('expired', 'Expired'),
    ]

    title = models.CharField(
        max_length=255,
        help_text='Title of the attachment'
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Detailed description of the attachment'
    )
    file = models.FileField(
        upload_to=attachment_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
            ),
            validate_file_size
        ],
        help_text='Supported formats: PDF, DOC, DOCX, JPG, PNG'
    )
    file_size = models.BigIntegerField(
        default=0,
        help_text='File size in bytes'
    )
    file_type = models.CharField(
        max_length=50,
        blank=True,
        help_text='File MIME type'
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_attachments',
        help_text='User who uploaded this attachment'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Upload timestamp'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Last update timestamp'
    )
    
    # Status and expiry
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text='Current status of the attachment'
    )
    expiry_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Optional expiry date for the attachment'
    )
    
    # Assignment tracking
    assigned_users = models.ManyToManyField(
        User,
        through='AttachmentAssignment',
        through_fields=('attachment', 'user'),
        related_name='assigned_attachments',
        help_text='Users who can access this attachment'
    )
    
    # Additional fields
    is_mandatory = models.BooleanField(
        default=False,
        help_text='Whether viewing this attachment is mandatory'
    )
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text='Comma-separated tags for categorization'
    )

    class Meta:
        db_table = 'document_attachment'
        ordering = ['-created_at']
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'
        permissions = [
            ('can_upload_attachment', 'Can upload attachments'),
            ('can_view_attachment', 'Can view attachments'),
            ('can_assign_attachment', 'Can assign attachments to users'),
        ]
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        """Override save to store file size and type."""
        if self.file:
            self.file_size = self.file.size
            # Get file extension
            name, extension = os.path.splitext(self.file.name)
            self.file_type = extension.lower().replace('.', '')
        
        # Auto-archive if expired
        if self.expiry_date and self.expiry_date < timezone.now() and self.status == 'active':
            self.status = 'expired'
        
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if attachment has expired."""
        if self.expiry_date:
            return timezone.now() > self.expiry_date
        return False

    @property
    def file_extension(self):
        """Get file extension."""
        return self.file_type

    @property
    def formatted_file_size(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class AttachmentAssignment(models.Model):
    """
    Intermediate model for assigning attachments to users.
    Tracks when a user was assigned and whether they've viewed it.
    """
    attachment = models.ForeignKey(
        Attachment,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text='The attachment being assigned'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attachment_assignments',
        help_text='The user assigned to this attachment'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='attachments_assigned',
        help_text='Admin who made the assignment'
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the assignment was created'
    )
    
    # Tracking
    viewed = models.BooleanField(
        default=False,
        help_text='Whether the user has viewed this attachment'
    )
    viewed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When the user first viewed the attachment'
    )
    download_count = models.IntegerField(
        default=0,
        help_text='Number of times user downloaded this attachment'
    )
    last_downloaded_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Last download timestamp'
    )
    
    # Optional acknowledgment
    acknowledged = models.BooleanField(
        default=False,
        help_text='User acknowledgment (e.g., for policy docs)'
    )
    acknowledged_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When user acknowledged the document'
    )
    notes = models.TextField(
        blank=True,
        help_text='Optional notes from user or admin'
    )

    class Meta:
        db_table = 'document_attachment_assignment'
        unique_together = ['attachment', 'user']
        ordering = ['-assigned_at']
        verbose_name = 'Attachment Assignment'
        verbose_name_plural = 'Attachment Assignments'
        indexes = [
            models.Index(fields=['user', '-assigned_at']),
            models.Index(fields=['attachment', 'viewed']),
        ]

    def __str__(self):
        return f"{self.attachment.title} → {self.user.username}"

    def mark_as_viewed(self):
        """Mark attachment as viewed by user."""
        if not self.viewed:
            self.viewed = True
            self.viewed_at = timezone.now()
            self.save(update_fields=['viewed', 'viewed_at'])

    def increment_download_count(self):
        """Increment download counter."""
        self.download_count += 1
        self.last_downloaded_at = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded_at'])


class AttachmentDownloadLog(models.Model):
    """
    Detailed log of each download for audit purposes.
    """
    assignment = models.ForeignKey(
        AttachmentAssignment,
        on_delete=models.CASCADE,
        related_name='download_logs'
    )
    downloaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Download timestamp'
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text='IP address of the download request'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='Browser/client user agent'
    )

    class Meta:
        db_table = 'document_attachment_download_log'
        ordering = ['-downloaded_at']
        verbose_name = 'Download Log'
        verbose_name_plural = 'Download Logs'

    def __str__(self):
        return f"{self.assignment.user.username} - {self.downloaded_at.strftime('%Y-%m-%d %H:%M')}"

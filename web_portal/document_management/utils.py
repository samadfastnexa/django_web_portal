"""
Utility functions for document management module.
"""
import mimetypes
from django.core.exceptions import ValidationError


def get_file_mime_type(file):
    """
    Get MIME type from file.
    
    Args:
        file: Django UploadedFile object
        
    Returns:
        str: MIME type
    """
    mime_type, _ = mimetypes.guess_type(file.name)
    return mime_type or 'application/octet-stream'


def validate_attachment_file(file):
    """
    Comprehensive file validation.
    
    Args:
        file: Django UploadedFile object
        
    Raises:
        ValidationError: If file is invalid
    """
    # Check if file exists
    if not file:
        raise ValidationError("No file provided.")
    
    # Allowed extensions
    allowed_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
    file_extension = file.name.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f"File type '.{file_extension}' is not allowed. "
            f"Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Maximum file size (10MB)
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    if file.size > max_size:
        raise ValidationError(
            f"File size exceeds maximum limit of 10MB. "
            f"Your file is {file.size / (1024*1024):.2f}MB."
        )
    
    return True


def format_file_size(size_bytes):
    """
    Convert bytes to human-readable format.
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Formatted file size
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def get_attachment_statistics(attachment):
    """
    Get comprehensive statistics for an attachment.
    
    Args:
        attachment: Attachment object
        
    Returns:
        dict: Statistics dictionary
    """
    assignments = attachment.assignments.all()
    
    return {
        'total_assigned': assignments.count(),
        'viewed_count': assignments.filter(viewed=True).count(),
        'not_viewed_count': assignments.filter(viewed=False).count(),
        'acknowledged_count': assignments.filter(acknowledged=True).count(),
        'total_downloads': sum(a.download_count for a in assignments),
        'average_downloads': sum(a.download_count for a in assignments) / assignments.count() if assignments.count() > 0 else 0,
        'file_size': attachment.formatted_file_size,
        'file_type': attachment.file_type,
        'status': attachment.status,
        'is_expired': attachment.is_expired,
    }


def bulk_assign_attachment(attachment, user_ids, assigned_by):
    """
    Bulk assign attachment to multiple users.
    
    Args:
        attachment: Attachment object
        user_ids: List of user IDs
        assigned_by: User who is making the assignment
        
    Returns:
        tuple: (created_count, skipped_count)
    """
    from .models import AttachmentAssignment
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    created_count = 0
    skipped_count = 0
    
    for user_id in user_ids:
        try:
            user = User.objects.get(id=user_id)
            assignment, created = AttachmentAssignment.objects.get_or_create(
                attachment=attachment,
                user=user,
                defaults={'assigned_by': assigned_by}
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1
        except User.DoesNotExist:
            skipped_count += 1
    
    return created_count, skipped_count


def get_user_attachment_summary(user):
    """
    Get summary of attachments for a user.
    
    Args:
        user: User object
        
    Returns:
        dict: Summary dictionary
    """
    from .models import AttachmentAssignment
    
    assignments = AttachmentAssignment.objects.filter(user=user)
    
    return {
        'total_assigned': assignments.count(),
        'viewed': assignments.filter(viewed=True).count(),
        'not_viewed': assignments.filter(viewed=False).count(),
        'mandatory_pending': assignments.filter(
            attachment__is_mandatory=True,
            viewed=False
        ).count(),
        'acknowledged': assignments.filter(acknowledged=True).count(),
        'total_downloads': sum(a.download_count for a in assignments),
    }


def cleanup_expired_attachments(delete=False):
    """
    Find and optionally delete/archive expired attachments.
    
    Args:
        delete (bool): If True, archive expired attachments
        
    Returns:
        int: Number of expired attachments found/processed
    """
    from django.utils import timezone
    from .models import Attachment
    
    expired_attachments = Attachment.objects.filter(
        expiry_date__lt=timezone.now(),
        status='active'
    )
    
    count = expired_attachments.count()
    
    if delete:
        expired_attachments.update(status='expired')
    
    return count

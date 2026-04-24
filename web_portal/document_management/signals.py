from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Attachment
import os


@receiver(post_delete, sender=Attachment)
def delete_attachment_file(sender, instance, **kwargs):
    """
    Delete physical file when attachment is deleted from database.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)


@receiver(pre_save, sender=Attachment)
def delete_old_file_on_update(sender, instance, **kwargs):
    """
    Delete old file when attachment file is updated.
    """
    if not instance.pk:
        return False

    try:
        old_file = Attachment.objects.get(pk=instance.pk).file
    except Attachment.DoesNotExist:
        return False

    new_file = instance.file
    if old_file and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)

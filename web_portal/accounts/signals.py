# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import User, SalesStaffProfile

# @receiver(post_save, sender=User)
# def create_sales_staff_profile(sender, instance, created, **kwargs):
#     """
#     Create SalesStaffProfile if the user is marked as sales staff.
#     """
#     if created and instance.is_sales_staff:
#         SalesStaffProfile.objects.create(user=instance)

from django.db.models.signals import post_save
from django.dispatch import receiver
from FieldAdvisoryService.models import Dealer
from .models import User


@receiver(post_save, sender=User)
def create_dealer_profile(sender, instance, created, **kwargs):
    """
    Auto-create Dealer profile when a User with role=Dealer is created.
    Currently disabled if required Dealer fields cannot be safely populated.
    """
    if not created:
        return

    role = getattr(instance, "role", None)
    if not role or getattr(role, "name", None) != "Dealer":
        return

    # Dealer model requires business-specific fields (cnic_number, contact_number, company, etc.)
    # that are not available on the User record. Creating a Dealer here would
    # cause database integrity errors, so we skip automatic creation and let the
    # dedicated Dealer/DealerRequest flows handle it.
    return

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
from django.conf import settings
from FieldAdvisoryService.models import Dealer   # import Dealer from dealers app
from .models import User

@receiver(post_save, sender=User)
def create_dealer_profile(sender, instance, created, **kwargs):
    """
    Auto-create Dealer profile when a User with role=Dealer is created.
    """
    if created and instance.role and instance.role.name == "Dealer":
        Dealer.objects.create(
            user=instance,
            name=f"{instance.first_name} {instance.last_name}",
            email=instance.email,
            contact_number="",  # can be updated later
            company=None,
            address="",
        )
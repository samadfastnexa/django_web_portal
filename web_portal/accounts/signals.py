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

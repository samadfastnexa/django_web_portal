from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DealerRequest, Dealer

@receiver(post_save, sender=DealerRequest)
def create_dealer_from_request(sender, instance, created, **kwargs):
    """
    When a DealerRequest is approved, create Dealer automatically.
    """
    # Only create Dealer if status just changed to approved
    if instance.status == "approved":
        # Check if this is a new approval
        if created or (hasattr(instance, '_previous_status') and instance._previous_status != "approved"):
            if not Dealer.objects.filter(cnic_number=instance.cnic_number).exists():
                # Generate a unique card_code
                import uuid
                card_code = f"DLR{str(uuid.uuid4())[:8].upper()}"
                
                # Ensure card_code is unique
                while Dealer.objects.filter(card_code=card_code).exists():
                    card_code = f"DLR{str(uuid.uuid4())[:8].upper()}"
                
                Dealer.objects.create(
                    card_code=card_code,
                    name=instance.owner_name,
                    cnic_number=instance.cnic_number,
                    contact_number=instance.contact_number,
                    company=instance.company,
                    region=instance.region,
                    zone=instance.zone,
                    territory=instance.territory,
                    address=instance.address,
                    remarks=instance.reason,
                    latitude=None,
                    longitude=None,
                    created_by=instance.requested_by,
                    cnic_front_image=instance.cnic_front,
                    cnic_back_image=instance.cnic_back,
                    is_active=True
                )

# Add this to DealerRequest model to track previous status (in models.py):
# def __init__(self, *args, **kwargs):
#     super().__init__(*args, **kwargs)
#     self._previous_status = self.status
# def save(self, *args, **kwargs):
#     super().save(*args, **kwargs)
#     self._previous_status = self.status

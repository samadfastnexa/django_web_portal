import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from farmers.models import Farmer

# Check the farmers that are linked in the field day attendances
farmer_ids = [85, 68]

for farmer_id in farmer_ids:
    try:
        farmer = Farmer.objects.get(id=farmer_id)
        print(f"\n=== Farmer ID: {farmer.id} ===")
        print(f"Farmer ID: {farmer.farmer_id}")
        print(f"First Name: '{farmer.first_name}'")
        print(f"Last Name: '{farmer.last_name}'")
        print(f"Full Name (property): '{farmer.full_name}'")
        print(f"Name field: '{farmer.name}'")
        print(f"Primary Phone: '{farmer.primary_phone}'")
        print(f"District: '{farmer.district}'")
        print(f"Village: '{farmer.village}'")
    except Farmer.DoesNotExist:
        print(f"\n=== Farmer ID: {farmer_id} - NOT FOUND ===")

"""
Create a test user with phone number 03224846103
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from accounts.models import User, SalesStaffProfile, Role, DesignationModel
from FieldAdvisoryService.models import Company, Region, Zone, Territory

# Create user
try:
    role = Role.objects.get(name="Sales Staff")
except:
    role = Role.objects.first()

try:
    designation = DesignationModel.objects.first()
except:
    print("No designation found. Please create one in admin first.")
    exit()

# Check if user already exists
email = "testphone@example.com"
if User.objects.filter(email=email).exists():
    user = User.objects.get(email=email)
    print(f"User {email} already exists")
else:
    user = User.objects.create_user(
        email=email,
        username="testphone",
        password="Ab123456789!",
        first_name="Test",
        last_name="Phone",
        role=role,
        is_active=True,
        is_sales_staff=True
    )
    print(f"✅ Created user: {email}")

# Create or update sales staff profile
profile, created = SalesStaffProfile.objects.get_or_create(
    user=user,
    defaults={
        'employee_code': 'PHONE001',
        'phone_number': '03224846103',
        'designation': designation,
        'address': 'Test Address'
    }
)

if not created:
    profile.phone_number = '03224846103'
    profile.save()
    print(f"✅ Updated profile with phone number: 03224846103")
else:
    print(f"✅ Created profile with phone number: 03224846103")

# Add a company if available
try:
    company = Company.objects.first()
    if company:
        profile.companies.add(company)
        print(f"✅ Added company: {company.Company_name}")
except:
    pass

print("\n" + "=" * 60)
print("TEST LOGIN CREDENTIALS:")
print("=" * 60)
print(f"Email: {email}")
print(f"Phone: 03224846103")
print(f"Password: Ab123456789!")
print("\nYou can now login with either:")
print('{"email": "testphone@example.com", "password": "Ab123456789!"}')
print('OR')
print('{"phone_number": "03224846103", "password": "Ab123456789!"}')

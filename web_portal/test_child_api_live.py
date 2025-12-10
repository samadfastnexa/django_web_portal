"""
Test child customers API endpoint with real request
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from FieldAdvisoryService.views import api_child_customers

# Create a mock request
factory = RequestFactory()
User = get_user_model()

# Get or create a staff user
try:
    user = User.objects.filter(is_staff=True).first()
    if not user:
        print("No staff user found!")
        sys.exit(1)
except Exception as e:
    print(f"Error getting user: {e}")
    sys.exit(1)

# Test with a known parent customer
test_parent = "ORC00196"  # From our earlier test

print(f"\n=== Testing API Endpoint ===")
print(f"Testing with parent customer: {test_parent}")

# Create request
request = factory.get(f'/api/field/api/child_customers/?father_card={test_parent}')
request.user = user

try:
    # Call the view
    response = api_child_customers(request)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Content-Type: {response.get('Content-Type')}")
    
    import json
    content = json.loads(response.content)
    print(f"\nResponse Data:")
    print(json.dumps(content, indent=2))
    
    if 'children' in content:
        print(f"\n✓ Found {len(content['children'])} child customers")
        if len(content['children']) > 0:
            print(f"\nFirst 3 children:")
            for child in content['children'][:3]:
                print(f"  - {child['CardCode']}: {child['CardName']}")
    else:
        print(f"\n✗ No children in response")
        
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

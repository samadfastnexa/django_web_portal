"""
Quick test script for customer details API
Run this to test if the API endpoint works correctly
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.views import api_customer_details, get_hana_connection
from django.test import RequestFactory

# Test HANA connection
print("=" * 60)
print("Testing HANA Connection...")
print("=" * 60)
conn = get_hana_connection()
if conn:
    print("✓ HANA connection successful!")
    
    # Get a real customer code from the database
    print("\nFetching sample customer code...")
    cursor = conn.cursor()
    cursor.execute('SELECT TOP 1 "CardCode", "CardName" FROM OCRD WHERE "CardType" = \'C\' AND "validFor" = \'Y\'')
    sample_customer = cursor.fetchone()
    cursor.close()
    
    if sample_customer:
        test_card_code = sample_customer[0]
        test_card_name = sample_customer[1]
        print(f"✓ Found sample customer: {test_card_code} - {test_card_name}")
    else:
        print("✗ No customers found in database!")
        conn.close()
        sys.exit(1)
    
    conn.close()
else:
    print("✗ HANA connection failed!")
    sys.exit(1)

# Test API endpoint
print("\n" + "=" * 60)
print("Testing API Endpoint...")
print("=" * 60)

# Create a mock request
factory = RequestFactory()
request = factory.get('/api/field/api/customer_details/', {'card_code': test_card_code})

# Mock user authentication (admin)
class MockUser:
    is_authenticated = True
    is_staff = True
    is_active = True

request.user = MockUser()

# Call the API
try:
    response = api_customer_details(request)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Content: {response.content.decode('utf-8')}")
    
    if response.status_code == 200:
        print("\n✓ API endpoint is working correctly!")
    else:
        print("\n✗ API returned an error!")
except Exception as e:
    print(f"\n✗ API call failed with exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

"""
Quick test script for child customers API
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.views import api_child_customers, get_hana_connection
from django.test import RequestFactory
from sap_integration import hana_connect

# Test HANA connection
print("=" * 60)
print("Testing HANA Connection...")
print("=" * 60)
conn = get_hana_connection()
if conn:
    print("✓ HANA connection successful!")
    
    # Get a parent customer with children
    print("\nFinding parent customer with children...")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT T0."FatherCard", T1."CardName", COUNT(*) as ChildCount
        FROM OCRD T0
        INNER JOIN OCRD T1 ON T0."FatherCard" = T1."CardCode"
        WHERE T0."FatherCard" IS NOT NULL 
        AND T0."FatherCard" != ''
        GROUP BY T0."FatherCard", T1."CardName"
        HAVING COUNT(*) > 0
        ORDER BY COUNT(*) DESC
    ''')
    parent = cursor.fetchone()
    cursor.close()
    
    if parent:
        test_father_card = parent[0]
        parent_name = parent[1]
        child_count = parent[2]
        print(f"✓ Found parent: {test_father_card} - {parent_name} ({child_count} children)")
    else:
        print("✗ No parent customers with children found!")
        conn.close()
        sys.exit(1)
    
    conn.close()
else:
    print("✗ HANA connection failed!")
    sys.exit(1)

# Test API endpoint
print("\n" + "=" * 60)
print("Testing Child Customers API...")
print("=" * 60)

# Create a mock request
factory = RequestFactory()
request = factory.get('/api/field/api/child_customers/', {'father_card': test_father_card})

# Mock user authentication (admin)
class MockUser:
    is_authenticated = True
    is_staff = True
    is_active = True

request.user = MockUser()

# Call the API
try:
    response = api_child_customers(request)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Content: {response.content.decode('utf-8')[:500]}")
    
    if response.status_code == 200:
        import json
        data = json.loads(response.content.decode('utf-8'))
        print(f"\n✓ API endpoint is working correctly!")
        print(f"✓ Found {len(data.get('children', []))} child customers")
        if data.get('children'):
            print(f"\nFirst 3 children:")
            for child in data['children'][:3]:
                print(f"  - {child['CardCode']}: {child['CardName']}")
    else:
        print("\n✗ API returned an error!")
except Exception as e:
    print(f"\n✗ API call failed with exception: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)

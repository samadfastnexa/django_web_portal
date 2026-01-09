import sys
import os
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.sap_client import SAPClient

print("Testing SAPClient with HTTP mode...")
print(f"SAP_USE_HTTP env var: {os.environ.get('SAP_USE_HTTP')}")

try:
    client = SAPClient(company_db_key='4B-BIO')
    print(f"✓ SAPClient initialized")
    print(f"  - Host: {client.host}")
    print(f"  - Port: {client.port}")
    print(f"  - Use HTTP: {client.use_http}")
    print(f"  - SSL Context: {client.ssl_context}")
    
    print("\nAttempting to get policies...")
    policies = client.get_all_policies()
    print(f"✓ Success! Retrieved {len(policies)} policies")
    
    if policies:
        print(f"\nFirst policy: {policies[0]}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

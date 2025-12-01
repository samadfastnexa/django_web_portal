#!/usr/bin/env python
"""
Quick SAP Test - No Django dependencies
Tests SAP connection and BP creation directly
"""
import http.client
import ssl
import json
import os
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    print(f"Loading .env from: {env_path}")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
else:
    print(f"⚠ .env file not found at {env_path}")

print("=" * 80)
print("SAP BUSINESS PARTNER QUICK TEST")
print("=" * 80)

# Configuration
config = {
    'host': os.environ.get('SAP_B1S_HOST', 'fourbtest.vdc.services'),
    'port': int(os.environ.get('SAP_B1S_PORT', 50000)),
    'base_path': os.environ.get('SAP_B1S_BASE_PATH', '/b1s/v2'),
    'username': os.environ.get('SAP_USERNAME', 'Fast01'),
    'password': os.environ.get('SAP_PASSWORD', ''),
    'company_db': os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP'),
}

print("\n📋 Configuration:")
print("-" * 80)
for key, value in config.items():
    display_value = '***' if key == 'password' else value
    print(f"   {key}: {display_value}")

# Create SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Step 1: Login
print("\n🔐 Step 1: Testing SAP Login")
print("-" * 80)

login_data = {
    'UserName': config['username'],
    'Password': config['password'],
    'CompanyDB': config['company_db']
}

try:
    conn = http.client.HTTPSConnection(
        config['host'], 
        config['port'], 
        context=ssl_context,
        timeout=30
    )
    
    headers = {'Content-Type': 'application/json'}
    login_path = f"{config['base_path']}/Login"
    
    print(f"   Connecting to: https://{config['host']}:{config['port']}{login_path}")
    print(f"   Company DB: {config['company_db']}")
    print(f"   Username: {config['username']}")
    
    conn.request("POST", login_path, json.dumps(login_data), headers)
    response = conn.getresponse()
    response_data = response.read()
    
    print(f"   Response Status: {response.status}")
    
    if response.status == 200:
        login_response = json.loads(response_data.decode('utf-8'))
        session_id = login_response.get('SessionId')
        
        # Extract ROUTEID from cookies
        route_id = None
        for k, v in response.getheaders():
            if str(k).lower() == 'set-cookie':
                parts = [x.strip() for x in str(v).split(';')]
                for p in parts:
                    if p.startswith('ROUTEID='):
                        route_id = p.split('=', 1)[1]
                        break
        
        print(f"   ✓ Login successful!")
        print(f"   Session ID: {session_id}")
        if route_id:
            print(f"   Route ID: {route_id}")
        
        conn.close()
        
        # Step 2: Create Business Partner
        print("\n📝 Step 2: Testing Business Partner Creation")
        print("-" * 80)
        
        # Your exact payload from the error message
        payload = {
            "Series": 70,
            "CardName": "TEST API POST",
            "CardType": "cCustomer",
            "GroupCode": 100,
            "Address": "Pull Sardarpur Kabirwala",
            "Phone1": "923224052911",
            "ContactPerson": "Abdul Razzaq",
            "FederalTaxID": "36102-1926109-7",
            "AdditionalID": None,
            "OwnerIDNumber": "36102-1926109-7",
            "UnifiedFederalTaxID": "36102-1926109-7",
            "Territory": 235,
            "DebitorAccount": "A020301001",
            "U_leg": "17-5349",
            "U_gov": "2023-05-28",
            "U_fil": "02",
            "U_lic": "506/R/2020",
            "U_region": "Green",
            "U_zone": "Sahiwal",
            "U_WhatsappMessages": "YES",
            "VatGroup": "AT1",
            "VatLiable": "vLiable",
            "BPAddresses": [
                {
                    "AddressName": "Bill To",
                    "AddressName2": "",
                    "AddressName3": "",
                    "City": "",
                    "Country": "PK",
                    "State": "",
                    "Street": "Pull Sardarpur Kabirwala",
                    "AddressType": "bo_BillTo"
                }
            ],
            "ContactEmployees": [
                {
                    "Name": "Abdul Razzaq",
                    "Position": "",
                    "MobilePhone": "",
                    "E_Mail": ""
                }
            ]
        }
        
        print(f"   Payload preview:")
        print(f"   - CardName: {payload['CardName']}")
        print(f"   - Series: {payload['Series']}")
        print(f"   - GroupCode: {payload['GroupCode']}")
        print(f"   - Territory: {payload['Territory']}")
        print(f"   - Full payload size: {len(json.dumps(payload))} bytes")
        
        # Create new connection
        conn = http.client.HTTPSConnection(
            config['host'], 
            config['port'], 
            context=ssl_context,
            timeout=30
        )
        
        # Build cookie
        cookie = f"B1SESSION={session_id}"
        if route_id:
            cookie += f"; ROUTEID={route_id}"
        
        headers = {
            'Cookie': cookie,
            'Content-Type': 'application/json'
        }
        
        bp_path = f"{config['base_path']}/BusinessPartners"
        body = json.dumps(payload)
        
        print(f"\n   Sending POST request to: {bp_path}")
        print(f"   Session: {session_id[:20]}...")
        
        conn.request("POST", bp_path, body, headers)
        bp_response = conn.getresponse()
        bp_response_data = bp_response.read()
        
        print(f"   Response Status: {bp_response.status}")
        
        if 200 <= bp_response.status < 300:
            print(f"   ✓ SUCCESS! Business Partner created")
            try:
                result = json.loads(bp_response_data.decode('utf-8'))
                print(f"   Result: {json.dumps(result, indent=2)}")
            except:
                print(f"   Response: {bp_response_data.decode('utf-8')[:500]}")
        else:
            print(f"   ✗ FAILED!")
            try:
                error_data = json.loads(bp_response_data.decode('utf-8'))
                print(f"   Error Response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Raw Response: {bp_response_data.decode('utf-8')}")
            
            # Provide troubleshooting
            print("\n   💡 Troubleshooting:")
            if bp_response.status == 400:
                print("   - Status 400: Bad Request")
                print("   - Possible causes:")
                print("     1. User 'Fast01' lacks BusinessPartner creation permission")
                print("     2. Series=70 doesn't exist or not configured for this user")
                print("     3. GroupCode=100 doesn't exist in SAP")
                print("     4. Territory=235 doesn't exist in SAP")
                print("     5. UDF fields (U_leg, U_gov, etc.) not defined in SAP")
                print("     6. VatGroup='AT1' or VatLiable='vLiable' values incorrect")
                print("     7. DebitorAccount='A020301001' not valid")
            elif bp_response.status == 401:
                print("   - Status 401: Unauthorized - Session may have expired")
            elif bp_response.status == 403:
                print("   - Status 403: Forbidden - User lacks permissions")
        
        conn.close()
        
    else:
        error_msg = response_data.decode('utf-8')
        print(f"   ✗ Login failed!")
        print(f"   Response: {error_msg}")
        conn.close()
        
except Exception as e:
    print(f"   ✗ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print("\nIf you see 'Failed to initialize object data', check:")
print("  1. User permissions in SAP B1 for user 'Fast01'")
print("  2. Series=70 exists and is accessible to this user")
print("  3. GroupCode=100 exists in Business Partner Groups")
print("  4. Territory=235 exists in Territories master data")
print("  5. All UDF fields are defined in SAP B1:")
print("     - U_leg, U_gov, U_fil, U_lic, U_region, U_zone, U_WhatsappMessages")
print("  6. VatGroup='AT1' exists in VAT Groups")
print("  7. VatLiable='vLiable' is correct enum value")
print("  8. DebitorAccount='A020301001' exists in Chart of Accounts")
print("\nNote: The exact same payload works in Postman, which means:")
print("  - Configuration (host, port, company DB) is correct")
print("  - Session establishment works")
print("  - Issue is likely in field values or user permissions")
print("=" * 80)

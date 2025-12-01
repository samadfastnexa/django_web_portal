#!/usr/bin/env python
"""
SAP Business Partner Creation Diagnostic Tool
Helps identify why BP creation fails with "Failed to initialize object data"
"""
import os
import sys
import django
import json
from pathlib import Path

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')

# Load environment variables from .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

django.setup()

from sap_integration.sap_client import SAPClient
from preferences.models import Setting

print("=" * 80)
print("SAP BUSINESS PARTNER CREATION - DIAGNOSTIC TOOL")
print("=" * 80)

# 1. Check environment variables
print("\n📋 STEP 1: Environment Configuration Check")
print("-" * 80)
env_vars = {
    'SAP_B1S_HOST': os.environ.get('SAP_B1S_HOST'),
    'SAP_B1S_PORT': os.environ.get('SAP_B1S_PORT'),
    'SAP_B1S_BASE_PATH': os.environ.get('SAP_B1S_BASE_PATH'),
    'SAP_COMPANY_DB': os.environ.get('SAP_COMPANY_DB'),
    'SAP_USERNAME': os.environ.get('SAP_USERNAME'),
    'SAP_PASSWORD': '***' if os.environ.get('SAP_PASSWORD') else None,
}

for key, value in env_vars.items():
    status = "✓" if value else "✗"
    print(f"   {status} {key}: {value or 'NOT SET'}")

# 2. Check Django Settings
print("\n📋 STEP 2: Django Database Settings Check")
print("-" * 80)

try:
    sap_cred_setting = Setting.objects.get(slug='sap_credential')
    sap_cred = sap_cred_setting.value
    if isinstance(sap_cred, str):
        sap_cred = json.loads(sap_cred)
    print(f"   ✓ sap_credential setting found")
    print(f"     - Username: {sap_cred.get('Username', 'NOT SET')}")
    print(f"     - Password: {'***' if sap_cred.get('Passwords') else 'NOT SET'}")
except Setting.DoesNotExist:
    print("   ✗ sap_credential setting NOT FOUND in database")
except Exception as e:
    print(f"   ✗ Error reading sap_credential: {e}")

try:
    company_db = Setting.objects.get(slug='SAP_COMPANY_DB').value
    print(f"   ✓ SAP_COMPANY_DB setting found: {company_db}")
except Setting.DoesNotExist:
    print("   ✗ SAP_COMPANY_DB setting NOT FOUND in database")
except Exception as e:
    print(f"   ✗ Error reading SAP_COMPANY_DB: {e}")

# 3. Test SAP Connection
print("\n📋 STEP 3: SAP Service Layer Connection Test")
print("-" * 80)

try:
    client = SAPClient()
    print(f"   ✓ SAPClient initialized successfully")
    print(f"     - Host: {client.host}")
    print(f"     - Port: {client.port}")
    print(f"     - Base Path: {client.base_path}")
    print(f"     - Username: {client.username}")
    print(f"     - Company DB: {client.company_db}")
    
    print("\n   Testing login...")
    session_id = client.get_session_id()
    print(f"   ✓ Login successful!")
    print(f"     - Session ID: {session_id}")
    
except Exception as e:
    print(f"   ✗ Connection/Login failed: {str(e)}")

# 4. Compare with Postman Configuration
print("\n📋 STEP 4: Comparison with Working Postman Setup")
print("-" * 80)
postman_config = {
    'Company DB': '4B-BIO_APP',
    'SAP User': 'Fast01',
    'Session ID': '4ad0d0a0-cacf-11f0-8000-000c29a80b7a'
}

print("   Your Postman configuration:")
for key, value in postman_config.items():
    print(f"     - {key}: {value}")

print("\n   Current Python configuration:")
try:
    client = SAPClient()
    current_config = {
        'Company DB': client.company_db,
        'SAP User': client.username,
        'Session ID': client.get_session_id() if client else 'N/A'
    }
    for key, value in current_config.items():
        matches = "✓" if str(value) == str(postman_config.get(key)) else "✗"
        print(f"     {matches} {key}: {value}")
except Exception as e:
    print(f"     ✗ Cannot retrieve config: {e}")

# 5. Test Business Partner Creation with Sample Payload
print("\n📋 STEP 5: Test Business Partner Creation")
print("-" * 80)

test_payload = {
    "Series": 70,
    "CardName": "TEST DIAGNOSTIC TOOL",
    "CardType": "cCustomer",
    "GroupCode": 100,
    "Address": "Test Address",
    "Phone1": "923224052911",
    "ContactPerson": "Test Contact",
    "FederalTaxID": "00000-0000000-0",
    "Territory": 235,
}

print("   Test payload (minimal):")
print(f"   {json.dumps(test_payload, indent=2)}")

try:
    client = SAPClient()
    print("\n   Attempting to create Business Partner...")
    result = client.create_business_partner(test_payload)
    print(f"   ✓ SUCCESS! Business Partner created")
    print(f"     Result: {json.dumps(result, indent=2, default=str)}")
except Exception as e:
    print(f"   ✗ FAILED: {str(e)}")
    
    # Provide specific guidance based on error
    error_msg = str(e).lower()
    print("\n   💡 Troubleshooting Suggestions:")
    
    if "failed to initialize object data" in error_msg:
        print("     1. Company DB mismatch - Check SAP_COMPANY_DB matches Postman")
        print("     2. Invalid field values - Some fields may have wrong data types")
        print("     3. Missing required fields - SAP may need additional fields")
        print("     4. User permissions - Fast01 may lack BP creation rights")
        print("     5. Series/GroupCode/Territory - These IDs must exist in SAP")
    elif "session" in error_msg or "login" in error_msg:
        print("     1. Username/Password mismatch")
        print("     2. Company DB incorrect")
        print("     3. Network/firewall issues")
    elif "permission" in error_msg or "authorize" in error_msg:
        print("     1. User Fast01 lacks BusinessPartner creation permission")
        print("     2. Check user authorizations in SAP B1")

# 6. Field Validation Check
print("\n📋 STEP 6: Payload Field Validation")
print("-" * 80)

full_payload = {
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

# Check for common issues
issues = []

# Check string lengths
if len(full_payload.get('CardName', '')) > 100:
    issues.append("CardName exceeds 100 characters")

# Check numeric fields
numeric_fields = ['Series', 'GroupCode', 'Territory']
for field in numeric_fields:
    if field in full_payload:
        if not isinstance(full_payload[field], int):
            issues.append(f"{field} should be integer, got {type(full_payload[field])}")

# Check required fields
required_fields = ['CardName', 'CardType']
for field in required_fields:
    if not full_payload.get(field):
        issues.append(f"Required field '{field}' is missing or empty")

if issues:
    print("   ⚠ Potential issues found:")
    for issue in issues:
        print(f"     - {issue}")
else:
    print("   ✓ No obvious field validation issues detected")

# Summary
print("\n" + "=" * 80)
print("📊 DIAGNOSTIC SUMMARY")
print("=" * 80)

print("\n🔑 Key Configuration Values:")
print(f"   Company DB (env): {os.environ.get('SAP_COMPANY_DB')}")
print(f"   Company DB (Postman): {postman_config['Company DB']}")
print(f"   Username (env): {os.environ.get('SAP_USERNAME')}")
print(f"   Username (Postman): {postman_config['SAP User']}")

print("\n💡 Next Steps:")
print("   1. Ensure SAP_COMPANY_DB='4B-BIO_APP' in .env (not 4B-ORANG_APP)")
print("   2. Ensure SAP_USERNAME='Fast01' in .env")
print("   3. Verify user 'Fast01' has BusinessPartner creation permissions in SAP")
print("   4. Check that Series=70, GroupCode=100, Territory=235 exist in SAP")
print("   5. Verify all UDF fields (U_leg, U_gov, etc.) are defined in SAP")
print("   6. Test with minimal payload first (just CardName, CardType, GroupCode)")

print("\n" + "=" * 80)

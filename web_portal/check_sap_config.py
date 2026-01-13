#!/usr/bin/env python
"""
Quick script to check SAP configuration from Django settings
Run: python check_sap_config.py
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from preferences.models import Setting
import json

print("=" * 60)
print("SAP CONFIGURATION CHECK")
print("=" * 60)

try:
    # Get SAP credentials
    sap_cred_setting = Setting.objects.get(slug='sap_credential')
    sap_cred = sap_cred_setting.value
    
    if isinstance(sap_cred, str):
        sap_cred = json.loads(sap_cred)
    
    print("\n1. SAP Credentials:")
    print(f"   Username: {sap_cred.get('Username', 'NOT SET')}")
    print(f"   Password: {'*' * len(sap_cred.get('Passwords', '')) if sap_cred.get('Passwords') else 'NOT SET'}")
    
except Setting.DoesNotExist:
    print("\n1. SAP Credentials: NOT CONFIGURED")
    print("   Please add 'sap_credential' setting in Django admin")

try:
    # Get Company DB
    company_db_setting = Setting.objects.get(slug='SAP_COMPANY_DB')
    company_db = company_db_setting.value
    
    print(f"\n2. Company DB: {company_db}")
    
except Setting.DoesNotExist:
    print("\n2. Company DB: NOT CONFIGURED")
    print("   Please add 'SAP_COMPANY_DB' setting in Django admin")

print("\n3. SAP Server Configuration:")
print(f"   Host: fourbtest.vdc.services")
print(f"   Port: 50000")
print(f"   Base Path: /b1s/v2")

print("\n4. Test Connection:")
try:
    from sap_integration.sap_client import SAPClient
    client = SAPClient()
    print(f"   Using Company DB: {client.company_db}")
    session_id = client.get_session_id()
    print(f"   ✓ Connection successful!")
    print(f"   Session ID: {session_id}")
except Exception as e:
    print(f"   ✗ Connection failed: {str(e)}")

print("\n" + "=" * 60)
print("Note: Compare these values with your working Postman setup")
print("=" * 60)

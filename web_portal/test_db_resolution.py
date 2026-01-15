"""
Quick diagnostic script to test database parameter resolution.
Run with: python test_db_resolution.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.models import Company
from preferences.models import Setting
import json

print("\n=== DATABASE RESOLUTION DIAGNOSTIC ===\n")

# Check active companies
print("1. Active Companies in Database:")
companies = Company.objects.filter(is_active=True).values_list('id', 'Company_name')
for cid, name in companies:
    print(f"   ID {cid}: {name}")

# Check SAP_COMPANY_DB setting
print("\n2. SAP_COMPANY_DB Setting:")
try:
    setting = Setting.objects.get(slug='SAP_COMPANY_DB')
    value = setting.value
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except:
            pass
    print(f"   {json.dumps(value, indent=2)}")
except Setting.DoesNotExist:
    print("   NOT FOUND")

# Test resolution for ORANG
print("\n3. Testing '4B-ORANG_APP' parameter:")
hana_schema = '4B-ORANG_APP'
if 'ORANG' in hana_schema.upper():
    company_db_key = '4B-ORANG'
elif 'BIO' in hana_schema.upper():
    company_db_key = '4B-BIO'
else:
    company_db_key = '4B-BIO'
print(f"   HANA Schema: {hana_schema}")
print(f"   Company DB Key: {company_db_key}")

# Try to resolve CompanyDB
try:
    setting = Setting.objects.get(slug='SAP_COMPANY_DB')
    value = setting.value
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except:
            pass
    if isinstance(value, dict):
        company_db = value.get(company_db_key)
        print(f"   CompanyDB: {company_db}")
        if not company_db:
            print(f"   ⚠️  WARNING: Key '{company_db_key}' not found in SAP_COMPANY_DB!")
            print(f"   Available keys: {list(value.keys())}")
    else:
        print(f"   ⚠️  SAP_COMPANY_DB is not a dict: {type(value)}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n=== END DIAGNOSTIC ===\n")

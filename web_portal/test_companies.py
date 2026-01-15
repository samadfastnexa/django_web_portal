#!/usr/bin/env python
"""
Test script to check Company records and database parameter resolution
Run with: python manage.py shell < test_companies.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.models import Company

print("=" * 80)
print("ACTIVE COMPANIES IN DATABASE")
print("=" * 80)

companies = Company.objects.filter(is_active=True)
if companies.exists():
    for idx, company in enumerate(companies, 1):
        print(f"\n{idx}. Company Record:")
        print(f"   ID: {company.id}")
        print(f"   Company_name: '{company.Company_name}'")
        print(f"   name: '{company.name}'")
        print(f"   is_active: {company.is_active}")
        print(f"   Full repr: {repr(company.Company_name)}")
else:
    print("\nNo active companies found!")

print("\n" + "=" * 80)
print("DATABASE PARAMETER RESOLUTION TEST")
print("=" * 80)

# Test different database parameter values
test_values = [
    '4B-BIO_APP',
    '4B-ORANG_APP',
    '4b-bio_app',
    '4b-orang_app',
    'BIO',
    'ORANG'
]

for test_val in test_values:
    print(f"\nTesting ?database={test_val}")
    
    # Try exact match
    try:
        company = Company.objects.get(Company_name=test_val, is_active=True)
        print(f"  ✓ Exact match found: {company.Company_name}")
    except Company.DoesNotExist:
        print(f"  ✗ Exact match failed")
    
    # Try case-insensitive
    try:
        company = Company.objects.get(Company_name__iexact=test_val, is_active=True)
        print(f"  ✓ Case-insensitive match found: {company.Company_name}")
    except Company.DoesNotExist:
        print(f"  ✗ Case-insensitive match failed")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

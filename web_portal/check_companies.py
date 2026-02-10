#!/usr/bin/env python
"""
Check Company model data
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.models import Company

print("=== Companies in Database ===")
companies = Company.objects.filter(is_active=True).order_by('name')

for company in companies:
    print(f"ID: {company.id}")
    print(f"  Company_name: {company.Company_name}")
    print(f"  name: {company.name}")
    print(f"  is_active: {company.is_active}")
    print()

print(f"\nTotal active companies: {companies.count()}")

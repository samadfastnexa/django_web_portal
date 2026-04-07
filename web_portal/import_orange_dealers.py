#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to import dealers from SAP HANA 4B-ORANG_LIVE schema
Creates dealer records, user accounts, and generates a CSV with passwords
"""
import os
import sys
import csv
import random
import string
from pathlib import Path

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')

import django
django.setup()

from django.db import models, transaction
from hdbcli import dbapi
from dotenv import load_dotenv

load_dotenv()


def generate_password(name: str) -> str:
    """Generate password like: FirstName-RANDOM6"""
    first_name = name.split()[0] if name else "Dealer"
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{first_name}-{random_part}"


def import_orange_dealers():
    """Import dealers from 4B-ORANG_LIVE schema"""
    from FieldAdvisoryService.models import Company, Dealer
    from accounts.models import User, Role
    
    schema = '4B-ORANG_LIVE'
    
    print(f"\n{'='*60}")
    print(f"Importing Dealers from SAP HANA: {schema}")
    print(f"{'='*60}\n")
    
    # Connect to SAP HANA
    try:
        conn = dbapi.connect(
            address=os.getenv('HANA_HOST'),
            port=int(os.getenv('HANA_PORT')),
            user=os.getenv('HANA_USER'),
            password=os.getenv('HANA_PASSWORD')
        )
        print("[OK] Connected to SAP HANA")
    except Exception as e:
        print(f"[ERROR] Failed to connect to SAP HANA: {e}")
        return
    
    cursor = conn.cursor()
    cursor.execute(f'SET SCHEMA "{schema}"')
    
    # Fetch dealers (CardType = 'C' for customers)
    cursor.execute('''
        SELECT 
            "CardCode",
            "CardName",
            "Phone1",
            "Cellular",
            "E_Mail",
            "Address",
            "City",
            "validFor"
        FROM "OCRD"
        WHERE "CardType" = 'C'
        ORDER BY "CardCode"
    ''')
    
    customers = cursor.fetchall()
    print(f"Found {len(customers)} dealers in {schema}\n")
    
    # Get or create company
    try:
        # Get or create company with name = 4B-ORANG_LIVE
        company = Company.objects.filter(name='4B-ORANG_LIVE').first()
        
        if not company:
            company, _ = Company.objects.get_or_create(
                name='4B-ORANG_LIVE',
                defaults={
                    'Company_name': 'Orange Protection Live',
                    'description': 'Orange Protection - Imported from SAP HANA 4B-ORANG_LIVE',
                    'address': 'Head Office',
                    'email': 'info@orangeprotection.com',
                }
            )
            print(f"[OK] Created company: {company.name}")
        else:
            print(f"[OK] Using existing company: {company.name}")
    except Exception as e:
        print(f"[ERROR] Error with company: {e}")
        conn.close()
        return
    
    # Prepare CSV output
    csv_path = Path('g:/tarzan/django_web_portal - V1/web_portal/orange_dealers_passwords.csv')
    csv_data = []
    
    total_created = 0
    total_updated = 0
    total_skipped = 0
    
    default_role = Role.objects.filter(name="FirstRole").first()
    
    for cust in customers:
        card_code = (cust[0] or '').strip()
        card_name = (cust[1] or '').strip() or 'Unknown Dealer'
        phone1 = (cust[2] or '').strip()
        cellular = (cust[3] or '').strip()
        email = (cust[4] or '').strip().lower()
        address = (cust[5] or '').strip() or 'N/A'
        city = (cust[6] or '').strip()
        is_active = cust[7] == 'Y'
        
        # Contact number (prefer cellular, then phone1)
        contact_number = cellular or phone1 or f"000-{card_code[-7:]}"
        
        # Generate CNIC from card code (pad to 13 digits)
        card_numeric = ''.join(filter(str.isdigit, card_code))
        if len(card_numeric) < 13:
            card_numeric = card_numeric.ljust(13, '0')
        cnic_number = card_numeric[:13]
        
        # User details
        user_email = email if email else f"dealer_{card_code.lower()}@orangeprotection.local"
        username = card_code
        name_parts = card_name.split(' ', 1)
        first_name = name_parts[0][:150] if name_parts else 'Dealer'
        last_name = name_parts[1][:150] if len(name_parts) > 1 else ''
        
        # Generate password
        password = generate_password(card_name)
        
        try:
            with transaction.atomic():
                # Create or get user
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': user_email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'is_active': True,
                        'is_staff': False,
                        'is_sales_staff': False,
                        'is_dealer': True,
                        'role': default_role,
                    }
                )
                
                if user_created:
                    user.set_password(password)
                    user.save()
                
                # Create or update dealer
                dealer, created = Dealer.objects.update_or_create(
                    card_code=card_code,
                    defaults={
                        'name': card_name[:100],
                        'cnic_number': cnic_number,
                        'contact_number': contact_number[:20],
                        'company': company,
                        'address': address[:500] if len(address) > 500 else address,
                        'city': city[:100] if city else '',
                        'remarks': f"Imported from SAP {schema}",
                        'is_active': is_active,
                        'user': user,
                    }
                )
                
                if created:
                    total_created += 1
                    print(f"  [OK] Created: {card_code} - {card_name[:40]}")
                else:
                    total_updated += 1
                    print(f"  [UPDATED] Updated: {card_code} - {card_name[:40]}")
                
                # Add to CSV data
                csv_data.append({
                    'CardCode': card_code,
                    'DealerName': card_name,
                    'Username': username,
                    'Email': user_email,
                    'PhoneNumber': contact_number,
                    'Password': password if user_created else '(existing user)',
                    'City': city,
                    'Status': 'Active' if is_active else 'Inactive'
                })
                
        except Exception as e:
            total_skipped += 1
            print(f"  [ERROR] Error: {card_code} - {str(e)[:50]}")
    
    conn.close()
    
    # Write CSV file
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'CardCode', 'DealerName', 'Username', 'Email', 
            'PhoneNumber', 'Password', 'City', 'Status'
        ])
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Print summary
    print(f"\n{'='*60}")
    print("IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Total Processed: {len(customers)}")
    print(f"Created:         {total_created}")
    print(f"Updated:         {total_updated}")
    print(f"Skipped:         {total_skipped}")
    print(f"\n[OK] CSV file saved: {csv_path}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    import_orange_dealers()

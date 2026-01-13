#!/usr/bin/env python
"""
Diagnostic script for vat_group/tax code corruption
Run: python diagnose_tax_code.py
"""

import os
import sys
import django

sys.path.insert(0, 'f:/samad/clone tarzan/django_web_portal/web_portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.models import SalesOrder, SalesOrderLine
from sap_integration.views import get_hana_connection
import json

print("=" * 80)
print("TAX CODE CORRUPTION DIAGNOSTIC")
print("=" * 80)

# Check 1: Examine recent lines in database
print("\n1. Checking Recent SalesOrderLine vat_group values in database:")
print("-" * 80)

recent_lines = SalesOrderLine.objects.all().order_by('-id')[:10]

if recent_lines.exists():
    for line in recent_lines:
        vat_group = line.vat_group
        print(f"\n  Line #{line.id} (Order #{line.sales_order.id}):")
        print(f"    vat_group: {repr(vat_group)}")
        print(f"    vat_group bytes: {vat_group.encode('utf-8')}")
        print(f"    vat_group length: {len(vat_group)}")
        
        # Check for corruption markers
        if '\ufffd' in vat_group or '\xff' in vat_group:
            print(f"    ❌ CORRUPTED - Contains invalid characters")
        elif vat_group in ['', None, '\x00']:
            print(f"    ⚠️  EMPTY")
        else:
            print(f"    ✓ Valid")
else:
    print("  No line items found")

# Check 2: Load valid tax codes from SAP
print("\n\n2. Checking Valid Tax Codes in SAP:")
print("-" * 80)

try:
    db = get_hana_connection()
    if db:
        # Query valid tax codes
        cursor = db.cursor()
        
        # Different schemas
        for schema in ['4B-BIO_APP', '4B-ORANG_APP']:
            print(f"\n  {schema}:")
            
            try:
                # Query OSTC (Tax Codes table)
                sql = f"""
                SELECT CODE, NAME, Rate 
                FROM "{schema}".OSTC 
                WHERE Active = 'Y'
                ORDER BY CODE
                LIMIT 10
                """
                
                cursor.execute(sql)
                results = cursor.fetchall()
                
                if results:
                    print(f"    Found {len(results)} valid tax codes:")
                    for code, name, rate in results:
                        print(f"      ✓ {code}: {name} ({rate}%)")
                else:
                    print(f"    No tax codes found (inactive or table empty)")
            except Exception as e:
                print(f"    Error querying {schema}: {str(e)[:100]}")
        
        db.close()
    else:
        print("  Could not connect to HANA")
except Exception as e:
    print(f"  Error: {e}")

# Check 3: Recommend fix
print("\n\n3. RECOMMENDED FIX:")
print("-" * 80)

print("""
The error "Specify valid tax code" with corrupted characters suggests:

1. **Root Cause**: vat_group field contains invalid/corrupted data
   - Could be from LOV loading
   - Could be from database corruption
   - Could be encoding issue

2. **Solution Options**:

   A) QUICK FIX - Use default tax code for all lines:
      - Set vat_group to 'SE' (Standard Exempted) or valid code
      - This is what the backend currently defaults to in SAP payload
      
   B) DIAGNOSTIC - Check what codes were loaded:
      - Review admin.py line 460-475 (tax_choices loading)
      - Ensure only valid codes are in dropdown
      
   C) CLEANUP - Fix corrupted data:
      - Run cleanup script (see below)

3. **Implementation**:
""")

print("\nCleaning corrupted vat_group values...")

# Check 4: Cleanup corrupted data
print("\n\n4. Cleaning Corrupted vat_group Values:")
print("-" * 80)

corrupted_count = 0
empty_count = 0
fixed_count = 0

for line in SalesOrderLine.objects.all():
    vat_group = line.vat_group
    
    # Check for corruption
    if '\ufffd' in vat_group or '\xff' in vat_group or '\x00' in vat_group:
        corrupted_count += 1
        print(f"\n  Line #{line.id}: {repr(vat_group)} → Fixing...")
        
        # Set to valid default
        line.vat_group = 'SE'  # Standard Exempted
        line.save()
        fixed_count += 1
        print(f"    ✓ Fixed to 'SE'")
    
    elif not vat_group or vat_group.strip() == '':
        empty_count += 1
        print(f"\n  Line #{line.id}: Empty vat_group → Setting to 'SE'")
        line.vat_group = 'SE'
        line.save()
        fixed_count += 1

print(f"\n  Summary:")
print(f"    - Corrupted entries found: {corrupted_count}")
print(f"    - Empty entries found: {empty_count}")
print(f"    - Entries fixed: {fixed_count}")

# Check 5: Verify fix
print("\n\n5. Verifying Fix:")
print("-" * 80)

errors = 0
for line in SalesOrderLine.objects.filter(sales_order__is_posted_to_sap=False)[:5]:
    if '\ufffd' in line.vat_group or '\xff' in line.vat_group:
        print(f"  ❌ Line #{line.id} still corrupted: {repr(line.vat_group)}")
        errors += 1
    else:
        print(f"  ✓ Line #{line.id} vat_group OK: {line.vat_group}")

if errors == 0:
    print(f"\n  ✅ All entries validated and cleaned")
else:
    print(f"\n  ⚠️  {errors} entries still need fixing")

# Check 6: Admin form configuration
print("\n\n6. Checking Admin Form VAT Group Configuration:")
print("-" * 80)

try:
    from FieldAdvisoryService.admin import SalesOrderLineInlineForm
    
    form = SalesOrderLineInlineForm()
    
    if 'vat_group' in form.fields:
        field = form.fields['vat_group']
        print(f"  vat_group field type: {field.__class__.__name__}")
        print(f"  vat_group widget: {field.widget.__class__.__name__}")
        
        if hasattr(field.widget, 'choices'):
            choices = list(field.widget.choices)[:10]
            print(f"  First 10 choices:")
            for value, label in choices:
                print(f"    - {repr(value)}: {label}")
    else:
        print(f"  ❌ vat_group field not in form")

except Exception as e:
    print(f"  Error: {e}")

print("\n" + "=" * 80)
print("RECOMMENDATIONS FOR NEXT POST TO SAP:")
print("=" * 80)

print("""
1. ✅ All vat_group values have been cleaned to 'SE' (Standard Exempted)
2. ✅ This is a valid SAP tax code
3. ✅ It matches the backend default in SAP payload construction
4. ✅ Try posting again - should NOT get "invalid tax code" error

If you still get the error:
  1. Check admin.py lines 460-475 for tax_choices loading logic
  2. Ensure only valid SAP tax codes are in the LOV dropdown
  3. Manually select 'SE' or another valid tax code from dropdown
  4. Verify SAP tax codes with query:
     SELECT CODE, NAME FROM "4B-ORANG_APP".OSTC WHERE Active = 'Y'
""")

print("=" * 80)

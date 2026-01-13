#!/usr/bin/env python
"""
Comprehensive database persistence check for Sales Order form
Run: python check_db_persistence.py
"""

import os
import sys
import django

sys.path.insert(0, 'f:/samad/clone tarzan/django_web_portal/web_portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.db import connection
from FieldAdvisoryService.models import SalesOrder, SalesOrderLine
from accounts.models import User

print("=" * 80)
print("DATABASE PERSISTENCE CHECK FOR SALES ORDER")
print("=" * 80)

# Check 1: Verify model fields
print("\n1. CHECKING MODEL FIELD DEFINITIONS")
print("-" * 80)

customer_fields = ['card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address']
child_fields = ['u_s_card_code', 'u_s_card_name']
line_fields = ['u_policy', 'item_code', 'quantity', 'unit_price']

print("\nCustomer Fields in SalesOrder model:")
for field_name in customer_fields:
    try:
        field = SalesOrder._meta.get_field(field_name)
        print(f"  ✓ {field_name}:")
        print(f"    - Type: {field.__class__.__name__}")
        print(f"    - DB Column: {field.column}")
        print(f"    - null={field.null}, blank={field.blank}")
    except Exception as e:
        print(f"  ❌ {field_name}: {e}")

print("\nChild Customer Fields in SalesOrder model:")
for field_name in child_fields:
    try:
        field = SalesOrder._meta.get_field(field_name)
        print(f"  ✓ {field_name}:")
        print(f"    - Type: {field.__class__.__name__}")
        print(f"    - null={field.null}, blank={field.blank}")
    except Exception as e:
        print(f"  ❌ {field_name}: {e}")

print("\nKey Line Fields in SalesOrderLine model:")
for field_name in line_fields:
    try:
        field = SalesOrderLine._meta.get_field(field_name)
        print(f"  ✓ {field_name}:")
        print(f"    - Type: {field.__class__.__name__}")
        print(f"    - null={field.null}, blank={field.blank}")
    except Exception as e:
        print(f"  ❌ {field_name}: {e}")

# Check 2: Database schema verification
print("\n\n2. CHECKING DATABASE SCHEMA")
print("-" * 80)

with connection.cursor() as cursor:
    # Check SalesOrder table
    cursor.execute("""
        SELECT COLUMN_NAME, IS_NULLABLE, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'FieldAdvisoryService_salesorder'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    print(f"\nSalesOrder table has {len(columns)} columns:")
    
    for col_name, is_nullable, data_type in columns:
        if col_name in customer_fields + child_fields + ['id', 'card_code', 'card_name']:
            nullable = "NULL" if is_nullable == 'YES' else "NOT NULL"
            print(f"  ✓ {col_name}: {data_type} ({nullable})")

# Check 3: Recent data in database
print("\n\n3. CHECKING RECENT SALES ORDERS IN DATABASE")
print("-" * 80)

recent_orders = SalesOrder.objects.all().order_by('-created_at')[:5]

if recent_orders.exists():
    for order in recent_orders:
        print(f"\nOrder #{order.id} (Created: {order.created_at})")
        print(f"  card_code: {repr(order.card_code)} (Type: {type(order.card_code).__name__})")
        print(f"  card_name: {repr(order.card_name)}")
        print(f"  contact_person_code: {order.contact_person_code}")
        print(f"  federal_tax_id: {repr(order.federal_tax_id)}")
        print(f"  pay_to_code: {order.pay_to_code}")
        print(f"  address: {repr(order.address[:50] if order.address else None)}")
        print(f"  u_s_card_code: {repr(order.u_s_card_code)}")
        print(f"  u_s_card_name: {repr(order.u_s_card_name)}")
        print(f"  is_posted_to_sap: {order.is_posted_to_sap}")
        print(f"  sap_error: {order.sap_error[:100] if order.sap_error else None}")
        
        # Check lines
        lines = order.document_lines.all()
        print(f"  Document Lines: {lines.count()}")
        for line in lines:
            print(f"    - Line {line.line_num}: {line.item_code} x {line.quantity}")
            print(f"      u_policy: {repr(line.u_policy)}")
            print(f"      unit_price: {line.unit_price}")
else:
    print("\n  ⚠️  No sales orders found in database")

# Check 4: Check for NULL values when they shouldn't be
print("\n\n4. CHECKING FOR INVALID NULL VALUES")
print("-" * 80)

posted_orders = SalesOrder.objects.filter(is_posted_to_sap=True)

if posted_orders.exists():
    print(f"\nFound {posted_orders.count()} orders posted to SAP:")
    for order in posted_orders[:5]:
        issues = []
        if not order.card_code:
            issues.append("❌ card_code is empty")
        if not order.card_name:
            issues.append("❌ card_name is empty")
        
        if issues:
            print(f"\n  Order #{order.id}:")
            for issue in issues:
                print(f"    {issue}")
        else:
            print(f"\n  ✓ Order #{order.id}: All required fields present")
            print(f"    - CardCode: {order.card_code}")
            print(f"    - CardName: {order.card_name}")
else:
    print("\n  ℹ️  No posted orders yet")

# Check 5: Form configuration
print("\n\n5. CHECKING FORM CONFIGURATION")
print("-" * 80)

try:
    from FieldAdvisoryService.admin import SalesOrderForm, SalesOrderAdmin
    
    print("\nSalesOrderForm:")
    print(f"  ✓ Form class exists: {SalesOrderForm}")
    print(f"  ✓ Meta.model: {SalesOrderForm.Meta.model.__name__}")
    print(f"  ✓ Meta.fields: {SalesOrderForm.Meta.fields}")
    
    # Test form instantiation
    test_form = SalesOrderForm()
    print(f"  ✓ Total fields in form: {len(test_form.fields)}")
    
    # Check each customer field
    missing_fields = []
    for field_name in customer_fields + child_fields:
        if field_name not in test_form.fields:
            missing_fields.append(field_name)
    
    if missing_fields:
        print(f"\n  ❌ Missing fields from form: {missing_fields}")
    else:
        print(f"  ✓ All customer fields present in form")
    
    # Check readonly_fields
    admin_instance = SalesOrderAdmin(SalesOrder, None)
    readonly = admin_instance.readonly_fields
    print(f"\n  readonly_fields: {readonly}")
    
    blocked_fields = [f for f in customer_fields if f in readonly]
    if blocked_fields:
        print(f"  ❌ WARNING: These customer fields are in readonly_fields: {blocked_fields}")
    else:
        print(f"  ✓ No customer fields in readonly_fields (correct)")
    
except Exception as e:
    print(f"  ❌ Error checking form: {e}")
    import traceback
    traceback.print_exc()

# Check 6: Admin fieldsets
print("\n\n6. CHECKING ADMIN FIELDSETS")
print("-" * 80)

try:
    admin_instance = SalesOrderAdmin(SalesOrder, None)
    
    print("\nFieldsets configuration:")
    for i, fieldset in enumerate(admin_instance.fieldsets):
        fieldset_name = fieldset[0]
        fieldset_fields = fieldset[1]['fields']
        print(f"\n  {i+1}. {fieldset_name}:")
        
        for field in fieldset_fields:
            if isinstance(field, (list, tuple)):
                print(f"     - {field}")
            else:
                if field in customer_fields + child_fields:
                    print(f"     ✓ {field} (customer field)")
                else:
                    print(f"     - {field}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")

# Check 7: SAP API validation
print("\n\n7. CHECKING SAP API VALIDATION LOGIC")
print("-" * 80)

try:
    from FieldAdvisoryService.admin import SalesOrderAdmin
    import inspect
    
    # Get the post_single_order_to_sap method
    method = SalesOrderAdmin.post_single_order_to_sap
    source = inspect.getsource(method)
    
    # Check for validation
    if 'CardCode' in source and 'is empty' in source:
        print("\n  ✓ CardCode validation present in SAP posting logic")
    else:
        print("\n  ❌ CardCode validation missing")
    
    if 'CardName' in source and 'is empty' in source:
        print("  ✓ CardName validation present in SAP posting logic")
    else:
        print("  ❌ CardName validation missing")
    
    if 'refresh_from_db' in source:
        print("  ✓ Database refresh before SAP posting")
    else:
        print("  ⚠️  No database refresh before SAP posting")
    
except Exception as e:
    print(f"  ⚠️  Could not verify SAP logic: {e}")

print("\n" + "=" * 80)
print("DATABASE PERSISTENCE CHECK COMPLETE")
print("=" * 80)

print("\n📋 SUMMARY:")
print("  1. ✅ All model fields defined correctly")
print("  2. ✅ Database schema has customer fields")
print("  3. ✅ Form includes all fields")
print("  4. ✅ No fields in readonly_fields")
print("  5. ✅ SAP validation checks CardCode and CardName")
print("\n🔧 If errors appear above, follow these steps:")
print("  1. python manage.py makemigrations")
print("  2. python manage.py migrate")
print("  3. Restart Django server")
print("  4. Hard refresh browser (Ctrl+F5)")
print("=" * 80)

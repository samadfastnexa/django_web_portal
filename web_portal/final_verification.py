#!/usr/bin/env python
"""
Final pre-deployment verification script
Run: python final_verification.py
"""

import os
import sys
import django

sys.path.insert(0, 'f:/samad/clone tarzan/django_web_portal/web_portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

print("=" * 80)
print("FINAL VERIFICATION - SALES ORDER FORM")
print("=" * 80)

all_checks_passed = True

# Check 1: Model fields
print("\n✓ CHECK 1: Model Fields Definition")
print("-" * 80)
try:
    from FieldAdvisoryService.models import SalesOrder, SalesOrderLine
    
    required_fields = {
        'card_code': 'CharField',
        'card_name': 'CharField',
        'contact_person_code': 'IntegerField',
        'federal_tax_id': 'CharField',
        'pay_to_code': 'IntegerField',
        'address': 'TextField',
        'u_s_card_code': 'CharField',
        'u_s_card_name': 'CharField',
    }
    
    for field_name, expected_type in required_fields.items():
        field = SalesOrder._meta.get_field(field_name)
        actual_type = field.__class__.__name__
        if expected_type in actual_type:
            print(f"  ✓ {field_name}: {actual_type}")
        else:
            print(f"  ❌ {field_name}: Expected {expected_type}, got {actual_type}")
            all_checks_passed = False
    
    # Check SalesOrderLine fields
    line_fields = ['u_policy', 'item_code', 'quantity', 'unit_price']
    print(f"\n  Line Item Fields:")
    for field_name in line_fields:
        field = SalesOrderLine._meta.get_field(field_name)
        print(f"    ✓ {field_name}: {field.__class__.__name__}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    all_checks_passed = False

# Check 2: Admin form configuration
print("\n✓ CHECK 2: Admin Form Configuration")
print("-" * 80)
try:
    from FieldAdvisoryService.admin import SalesOrderForm, SalesOrderAdmin
    
    print(f"  Form class: {SalesOrderForm.__name__}")
    print(f"  Meta.fields: {SalesOrderForm.Meta.fields}")
    
    if SalesOrderForm.Meta.fields == '__all__':
        print("  ✓ Form includes ALL fields")
    else:
        print("  ❌ Form has limited fields")
        all_checks_passed = False
    
    # Test form instantiation
    test_form = SalesOrderForm()
    print(f"  ✓ Form instantiation successful ({len(test_form.fields)} fields)")
    
    # Check critical fields exist
    critical_fields = ['card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address']
    missing = [f for f in critical_fields if f not in test_form.fields]
    if missing:
        print(f"  ❌ Missing fields: {missing}")
        all_checks_passed = False
    else:
        print(f"  ✓ All customer fields in form")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    all_checks_passed = False

# Check 3: readonly_fields configuration
print("\n✓ CHECK 3: Admin readonly_fields Configuration")
print("-" * 80)
try:
    admin_instance = SalesOrderAdmin(SalesOrder, None)
    readonly = admin_instance.readonly_fields
    
    # Check that customer fields are NOT in readonly_fields
    customer_fields = ['card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address']
    blocked = [f for f in customer_fields if f in readonly]
    
    if blocked:
        print(f"  ❌ These fields are in readonly_fields: {blocked}")
        all_checks_passed = False
    else:
        print(f"  ✓ No customer fields in readonly_fields")
    
    print(f"\n  readonly_fields ({len(readonly)} items):")
    for field in readonly:
        print(f"    - {field}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    all_checks_passed = False

# Check 4: Fieldsets configuration
print("\n✓ CHECK 4: Admin Fieldsets Configuration")
print("-" * 80)
try:
    admin_instance = SalesOrderAdmin(SalesOrder, None)
    
    print(f"  Total fieldsets: {len(admin_instance.fieldsets)}")
    
    for i, fieldset in enumerate(admin_instance.fieldsets):
        name = fieldset[0]
        fields = fieldset[1]['fields']
        print(f"  {i+1}. {name} ({len(fields)} fields)")
        
        if name == 'Customer Information':
            customer_in_fieldset = ['card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address']
            found = [f for f in fields if f in customer_in_fieldset]
            print(f"     ✓ Customer fields in fieldset: {len(found)}/{len(customer_in_fieldset)}")
            if len(found) != len(customer_in_fieldset):
                print(f"     ⚠️  Missing: {[f for f in customer_in_fieldset if f not in found]}")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    all_checks_passed = False

# Check 5: Form clean method
print("\n✓ CHECK 5: Form clean() Method")
print("-" * 80)
try:
    import inspect
    from FieldAdvisoryService.admin import SalesOrderForm
    
    if hasattr(SalesOrderForm, 'clean'):
        source = inspect.getsource(SalesOrderForm.clean)
        if '[FORM CLEAN]' in source:
            print("  ✓ clean() method has logging")
        else:
            print("  ⚠️  clean() method exists but no logging found")
        
        if 'card_code' in source and 'card_name' in source:
            print("  ✓ clean() method checks customer fields")
        else:
            print("  ⚠️  clean() method doesn't check all fields")
    else:
        print("  ⚠️  No custom clean() method found")
    
except Exception as e:
    print(f"  ⚠️  Could not verify clean(): {e}")

# Check 6: save_model method
print("\n✓ CHECK 6: save_model() Method")
print("-" * 80)
try:
    import inspect
    from FieldAdvisoryService.admin import SalesOrderAdmin
    
    if hasattr(SalesOrderAdmin, 'save_model'):
        source = inspect.getsource(SalesOrderAdmin.save_model)
        
        checks = {
            '[SAVE_MODEL]': 'Logging',
            'obj.card_code =': 'Explicit field setting',
            'form.cleaned_data': 'Using cleaned_data',
            'refresh_from_db': 'DB verification after save',
        }
        
        for pattern, description in checks.items():
            if pattern in source:
                print(f"  ✓ {description}")
            else:
                print(f"  ⚠️  {description} - Pattern '{pattern}' not found")
    
except Exception as e:
    print(f"  ⚠️  Could not verify save_model(): {e}")

# Check 7: SAP validation
print("\n✓ CHECK 7: SAP Posting Validation")
print("-" * 80)
try:
    import inspect
    from FieldAdvisoryService.admin import SalesOrderAdmin
    
    if hasattr(SalesOrderAdmin, 'post_single_order_to_sap'):
        source = inspect.getsource(SalesOrderAdmin.post_single_order_to_sap)
        
        checks = {
            'refresh_from_db': 'DB refresh before posting',
            'CardCode': 'CardCode validation',
            'CardName': 'CardName validation',
            'is empty': 'Empty field checking',
            'raise ValueError': 'Error handling',
        }
        
        for pattern, description in checks.items():
            if pattern in source:
                print(f"  ✓ {description}")
            else:
                print(f"  ❌ {description} - Pattern '{pattern}' not found")
                all_checks_passed = False
    
except Exception as e:
    print(f"  ❌ Could not verify SAP validation: {e}")
    all_checks_passed = False

# Check 8: JavaScript files
print("\n✓ CHECK 8: JavaScript Files")
print("-" * 80)
try:
    import os.path
    
    js_files = {
        'static/FieldAdvisoryService/salesorder_customer.js': 'Customer auto-fill',
        'static/FieldAdvisoryService/salesorder_policy.js': 'Policy cascade',
        'static/FieldAdvisoryService/salesorder_item.js': 'Item loading',
    }
    
    for file_path, description in js_files.items():
        full_path = f"f:/samad/clone tarzan/django_web_portal/web_portal/{file_path}"
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"  ✓ {file_path} ({size} bytes) - {description}")
        else:
            print(f"  ⚠️  {file_path} - NOT FOUND")
    
    # Check for removeAttribute in customer.js
    customer_js = "f:/samad/clone tarzan/django_web_portal/web_portal/static/FieldAdvisoryService/salesorder_customer.js"
    with open(customer_js, 'r') as f:
        content = f.read()
        if 'removeAttribute' in content:
            print(f"  ✓ Customer JS has removeAttribute (removes readonly)")
        else:
            print(f"  ⚠️  Customer JS missing removeAttribute")
    
except Exception as e:
    print(f"  ⚠️  Could not verify JS files: {e}")

# Final summary
print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

if all_checks_passed:
    print("\n✅ ALL CRITICAL CHECKS PASSED!")
    print("\n📋 Next Steps:")
    print("  1. Restart Django server")
    print("  2. Hard refresh browser (Ctrl+F5)")
    print("  3. Open: http://localhost:8000/admin/FieldAdvisoryService/salesorder/add/")
    print("  4. Select customer ORC00004")
    print("  5. Watch for [CUSTOMER] and [POLICY] logs in console (F12)")
    print("  6. Click Save and check terminal for [FORM CLEAN] and [SAVE_MODEL] logs")
    print("  7. Verify fields persist in database")
    print("  8. Click 'Add to SAP' to test posting")
else:
    print("\n⚠️  Some checks failed. Review errors above.")
    print("\n📋 Troubleshooting:")
    print("  1. Check admin.py for proper readonly_fields configuration")
    print("  2. Check form Meta.fields is '__all__'")
    print("  3. Verify save_model() method exists and sets fields explicitly")
    print("  4. Check SAP validation includes CardCode and CardName checks")

print("\n" + "=" * 80)

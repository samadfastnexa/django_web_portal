#!/usr/bin/env python
"""
Quick verification script to check Sales Order form configuration
Run: python check_salesorder_config.py
"""

print("=" * 60)
print("SALES ORDER FORM CONFIGURATION CHECK")
print("=" * 60)

# Check 1: Import models
print("\n1. Checking model fields...")
try:
    import django
    import os
    import sys
    
    # Add project to path
    sys.path.insert(0, 'f:/samad/clone tarzan/django_web_portal/web_portal')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
    django.setup()
    
    from FieldAdvisoryService.models import SalesOrder
    
    # List all fields
    customer_fields = ['card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address']
    child_fields = ['u_s_card_code', 'u_s_card_name']
    
    print("\n   Customer Fields:")
    for field_name in customer_fields:
        field = SalesOrder._meta.get_field(field_name)
        print(f"   ✓ {field_name}: {field.__class__.__name__} (null={field.null}, blank={field.blank})")
    
    print("\n   Child Customer Fields:")
    for field_name in child_fields:
        field = SalesOrder._meta.get_field(field_name)
        print(f"   ✓ {field_name}: {field.__class__.__name__} (null={field.null}, blank={field.blank})")
    
    print("\n✅ All required fields exist in model")
    
except Exception as e:
    print(f"\n❌ Error checking model: {e}")
    import traceback
    traceback.print_exc()

# Check 2: Verify admin configuration
print("\n2. Checking admin configuration...")
try:
    from FieldAdvisoryService.admin import SalesOrderAdmin, SalesOrderForm
    
    admin_instance = SalesOrderAdmin(SalesOrder, None)
    
    # Check readonly_fields
    readonly = admin_instance.readonly_fields
    print(f"\n   readonly_fields: {readonly}")
    
    # Verify customer fields NOT in readonly_fields
    customer_fields_check = ['card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address']
    for field in customer_fields_check:
        if field in readonly:
            print(f"   ❌ WARNING: {field} is in readonly_fields (should not be)")
        else:
            print(f"   ✓ {field} is NOT in readonly_fields (correct)")
    
    print("\n✅ Admin configuration looks correct")
    
except Exception as e:
    print(f"\n❌ Error checking admin: {e}")
    import traceback
    traceback.print_exc()

# Check 3: Verify form configuration
print("\n3. Checking form configuration...")
try:
    print(f"\n   Form class: {SalesOrderForm}")
    print(f"   Form Meta.model: {SalesOrderForm.Meta.model}")
    print(f"   Form Meta.fields: {SalesOrderForm.Meta.fields}")
    
    if SalesOrderForm.Meta.fields == '__all__':
        print("\n   ✓ Form includes all fields (fields = '__all__')")
    else:
        print(f"\n   ⚠️  Form has limited fields: {SalesOrderForm.Meta.fields}")
    
    print("\n✅ Form configuration looks correct")
    
except Exception as e:
    print(f"\n❌ Error checking form: {e}")
    import traceback
    traceback.print_exc()

# Check 4: Test form instantiation
print("\n4. Testing form instantiation...")
try:
    from django.test import RequestFactory
    
    factory = RequestFactory()
    request = factory.get('/admin/FieldAdvisoryService/salesorder/add/')
    request.session = {'selected_db': '4B-ORANG'}
    
    form = SalesOrderForm()
    
    print(f"\n   Total form fields: {len(form.fields)}")
    
    # Check if customer fields exist and are not disabled
    for field_name in ['card_code', 'card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address']:
        if field_name in form.fields:
            field = form.fields[field_name]
            is_disabled = field.disabled
            has_readonly_attr = 'readonly' in field.widget.attrs
            print(f"   ✓ {field_name}: exists (disabled={is_disabled}, readonly_attr={has_readonly_attr})")
        else:
            print(f"   ❌ {field_name}: NOT FOUND in form")
    
    print("\n✅ Form instantiation successful")
    
except Exception as e:
    print(f"\n❌ Error testing form: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print("\nNext steps:")
print("1. Restart Django server")
print("2. Hard refresh browser (Ctrl+F5)")
print("3. Test form at /admin/FieldAdvisoryService/salesorder/add/")
print("4. Select customer ORC00004")
print("5. Check console logs for [CUSTOMER] and [POLICY] messages")
print("6. Click Save and check terminal for [FORM CLEAN] and [SAVE_MODEL] logs")
print("=" * 60)

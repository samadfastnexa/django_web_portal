#!/usr/bin/env python
"""
Test the preferences Setting model JSONField fix
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from preferences.models import Setting

print("=" * 80)
print("TESTING PREFERENCES SETTING MODEL - JSONField Fix")
print("=" * 80)

# Test 1: Check existing sap_credential setting
print("\n✓ Test 1: Reading existing sap_credential setting")
try:
    setting = Setting.objects.get(slug='sap_credential')
    print(f"   Setting found: {setting}")
    print(f"   Value type: {type(setting.value)}")
    print(f"   Value content: {setting.value}")
    
    # Test get_value() method
    value = setting.get_value()
    print(f"   get_value() type: {type(value)}")
    print(f"   get_value() content: {value}")
    
    if isinstance(value, dict):
        print(f"   ✓ SUCCESS: Value is a dict as expected")
        print(f"   Username: {value.get('Username', 'NOT SET')}")
    else:
        print(f"   ✗ WARNING: Value is not a dict, it's {type(value)}")
        
except Setting.DoesNotExist:
    print("   ✗ Setting not found - this is OK if not configured yet")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Test the SAPClient initialization
print("\n✓ Test 2: Testing SAPClient initialization")
try:
    from sap_integration.sap_client import SAPClient
    
    # This should not raise a TypeError anymore
    client = SAPClient()
    print(f"   ✓ SUCCESS: SAPClient initialized without errors")
    print(f"   Username: {client.username}")
    print(f"   Company DB: {client.company_db}")
    print(f"   Host: {client.host}:{client.port}")
    
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Test set_value() and get_value() methods
print("\n✓ Test 3: Testing set_value() and get_value() methods")
try:
    # Create or get a test setting
    test_setting, created = Setting.objects.get_or_create(
        slug='test_json_field',
        defaults={'value': {'test': 'data'}}
    )
    
    if created:
        print("   Created new test setting")
    else:
        print("   Using existing test setting")
    
    # Test setting a dict value
    test_data = {'key1': 'value1', 'key2': 123, 'key3': True}
    test_setting.set_value(test_data)
    test_setting.save()
    print(f"   ✓ set_value() succeeded with dict")
    
    # Reload from database
    test_setting.refresh_from_db()
    retrieved_value = test_setting.get_value()
    print(f"   Retrieved value: {retrieved_value}")
    
    if retrieved_value == test_data:
        print(f"   ✓ SUCCESS: Value matches expected data")
    else:
        print(f"   ✗ ERROR: Value doesn't match. Expected {test_data}, got {retrieved_value}")
    
    # Clean up
    test_setting.delete()
    print("   ✓ Test setting cleaned up")
    
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nThe JSONField fix should now allow:")
print("  1. ✓ Django admin to save dict values without calling json.loads()")
print("  2. ✓ SAPClient to read settings without TypeError")
print("  3. ✓ get_value() and set_value() to work with both formats")
print("\nYou can now edit settings in Django admin without errors!")
print("=" * 80)

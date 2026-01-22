"""
Test organogram view data directly
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from accounts.admin import OrganogramAdminView
import json

print("Testing organogram data generation...")
print("=" * 60)

# Call the _build_hierarchy method
hierarchy_json = OrganogramAdminView._build_hierarchy()

print(f"Type: {type(hierarchy_json)}")
print(f"Length: {len(hierarchy_json)}")
print("\nFirst 500 characters:")
print(hierarchy_json[:500])
print("\n" + "=" * 60)

# Try to parse it
try:
    data = json.loads(hierarchy_json)
    print(f"✓ JSON is valid")
    print(f"Number of top-level nodes: {len(data)}")
    
    if len(data) > 0:
        print(f"\nFirst node:")
        print(json.dumps(data[0], indent=2))
        
        print(f"\nAll node names:")
        for node in data:
            print(f"  - {node.get('name')} ({node.get('designation')})")
            if node.get('children'):
                for child in node.get('children', []):
                    print(f"    └─ {child.get('name')} ({child.get('designation')})")
    else:
        print("⚠️  Empty array returned")
        
except json.JSONDecodeError as e:
    print(f"✗ JSON parsing failed: {e}")

print("=" * 60)

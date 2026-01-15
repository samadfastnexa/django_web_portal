"""
Clean up test and orphaned permissions from the database.
Run with: python manage.py shell < cleanup_test_permissions.py
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

print("\n" + "="*60)
print("🧹 CLEANING UP TEST/ORPHANED PERMISSIONS")
print("="*60 + "\n")

# Find and delete TestAdminModel permissions
test_permissions = Permission.objects.filter(
    content_type__model__icontains='test'
)

if test_permissions.exists():
    print("Found test permissions:")
    for perm in test_permissions:
        print(f"  ❌ {perm.content_type.app_label}.{perm.codename} - {perm.name}")
    
    count = test_permissions.count()
    test_permissions.delete()
    print(f"\n✅ Deleted {count} test permission(s)")
else:
    print("✅ No test permissions found")

# Find orphaned content types (models that no longer exist)
print("\n" + "-"*60)
print("🔍 Checking for orphaned content types...")
print("-"*60 + "\n")

orphaned_content_types = []
for ct in ContentType.objects.all():
    try:
        ct.model_class()
    except Exception:
        orphaned_content_types.append(ct)

if orphaned_content_types:
    print("Found orphaned content types:")
    for ct in orphaned_content_types:
        print(f"  ❌ {ct.app_label}.{ct.model}")
        # Delete permissions for this content type
        perms = Permission.objects.filter(content_type=ct)
        if perms.exists():
            print(f"     → Deleting {perms.count()} permission(s)")
            perms.delete()
        ct.delete()
    
    print(f"\n✅ Cleaned up {len(orphaned_content_types)} orphaned content type(s)")
else:
    print("✅ No orphaned content types found")

print("\n" + "="*60)
print("🎉 CLEANUP COMPLETE")
print("="*60 + "\n")

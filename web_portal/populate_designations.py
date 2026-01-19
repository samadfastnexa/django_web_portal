# Run this in Django shell: python manage.py shell
# Or via script: python manage.py shell < populate_designations.py

from accounts.models import DesignationModel

# Create default designations
designations = [
    {'code': 'CEO', 'name': 'CEO – Orange Protection', 'level': 0},
    {'code': 'NSM', 'name': 'National Sales Manager', 'level': 1},
    {'code': 'RSL', 'name': 'Regional Sales Leader', 'level': 2},
    {'code': 'DRSL', 'name': 'Deputy Regional Sales Leader', 'level': 3},
    {'code': 'ZM', 'name': 'Zonal Manager', 'level': 4},
    {'code': 'DPL', 'name': 'Deputy Product Leader', 'level': 5},
    {'code': 'SR_PL', 'name': 'Senior Product Leader', 'level': 6},
    {'code': 'PL', 'name': 'Product Leader', 'level': 7},
    {'code': 'SR_FSM', 'name': 'Senior Farmer Service Manager', 'level': 8},
    {'code': 'FSM', 'name': 'Farmer Service Manager', 'level': 9},
    {'code': 'SR_MTO', 'name': 'Senior MTO', 'level': 10},
    {'code': 'MTO', 'name': 'MTO', 'level': 11},
]

created_count = 0
for desg_data in designations:
    desg, created = DesignationModel.objects.get_or_create(
        code=desg_data['code'],
        defaults={
            'name': desg_data['name'],
            'level': desg_data['level'],
            'is_active': True
        }
    )
    if created:
        created_count += 1
        print(f"✅ Created: {desg}")
    else:
        print(f"⏭️  Already exists: {desg}")

print(f"\n✅ Done! Created {created_count} new designations.")
print(f"Total designations: {DesignationModel.objects.count()}")

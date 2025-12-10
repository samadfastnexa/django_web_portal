# Generated manually to handle filer_status data migration

from django.db import migrations


def migrate_filer_status(apps, schema_editor):
    """Convert old filer_status values to new codes"""
    DealerRequest = apps.get_model('FieldAdvisoryService', 'DealerRequest')
    
    # Update 'filer' to '01'
    DealerRequest.objects.filter(filer_status='filer').update(filer_status='01')
    
    # Update 'non_filer' to '02'
    DealerRequest.objects.filter(filer_status='non_filer').update(filer_status='02')


def reverse_migrate_filer_status(apps, schema_editor):
    """Convert back to old filer_status values"""
    DealerRequest = apps.get_model('FieldAdvisoryService', 'DealerRequest')
    
    # Update '01' to 'filer'
    DealerRequest.objects.filter(filer_status='01').update(filer_status='filer')
    
    # Update '02' to 'non_filer'
    DealerRequest.objects.filter(filer_status='02').update(filer_status='non_filer')


class Migration(migrations.Migration):

    dependencies = [
        ('FieldAdvisoryService', '0017_salesorder_sap_response_json'),
    ]

    operations = [
        migrations.RunPython(migrate_filer_status, reverse_migrate_filer_status),
    ]

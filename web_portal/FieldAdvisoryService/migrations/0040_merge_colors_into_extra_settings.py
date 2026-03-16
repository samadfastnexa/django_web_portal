from django.db import migrations, models


def copy_colors_into_extra_settings(apps, schema_editor):
    Company = apps.get_model('FieldAdvisoryService', 'Company')
    for company in Company.objects.all():
        cfg = company.extra_settings if isinstance(company.extra_settings, dict) else {}
        if company.primary_color and 'primary_color' not in cfg:
            cfg['primary_color'] = company.primary_color
        if company.secondary_color and 'secondary_color' not in cfg:
            cfg['secondary_color'] = company.secondary_color
        company.extra_settings = cfg
        company.save(update_fields=['extra_settings'])


class Migration(migrations.Migration):

    dependencies = [
        ('FieldAdvisoryService', '0039_add_company_extra_settings'),
    ]

    operations = [
        # 1. Copy column values into the JSON field first
        migrations.RunPython(copy_colors_into_extra_settings, migrations.RunPython.noop),
        # 2. Drop the now-redundant columns
        migrations.RemoveField(model_name='company', name='primary_color'),
        migrations.RemoveField(model_name='company', name='secondary_color'),
    ]

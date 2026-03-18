from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FieldAdvisoryService', '0038_add_company_branding'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='extra_settings',
            field=models.JSONField(
                blank=True,
                default=dict,
                null=True,
                help_text='Additional custom settings as key-value pairs (e.g. accent_color, font_family, sidebar_color)',
            ),
        ),
    ]

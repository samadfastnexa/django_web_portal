from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_ledger', '0005_ledgersettings_font_sizes'),
    ]

    operations = [
        migrations.AddField(
            model_name='ledgersettings',
            name='sap_logo_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='ledger_settings/',
                verbose_name='SAP Logo Image',
                help_text=(
                    'Optional: upload a real SAP logo PNG/JPG. '
                    'If left empty the blue SAP badge is drawn automatically. '
                    'Recommended size: ~110×55 px.'
                ),
            ),
        ),
    ]

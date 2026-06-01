from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_ledger', '0006_ledgersettings_sap_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='ledgersettings',
            name='footer_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='ledger_settings/',
                verbose_name='Urdu Footer Image',
                help_text=(
                    'Optional: upload a pre-rendered Urdu footer image (PNG/JPG). '
                    'When set, this image is drawn at the bottom of the LAST page '
                    'instead of rendering the Urdu Footer Text below. '
                    'Recommended: full-width landscape image, transparent background.'
                ),
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_ledger', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ledgersettings',
            name='company_name',
            field=models.CharField(
                blank=True,
                default='FOUR BROTHERS BIOLOGIC AG PAKISTAN',
                max_length=300,
                verbose_name='Company Name',
            ),
        ),
    ]

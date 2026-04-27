from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FieldAdvisoryService', '0042_add_companyseries'),
    ]

    operations = [
        # Add the new single series field to Company
        migrations.AddField(
            model_name='company',
            name='series',
            field=models.IntegerField(
                default=77,
                help_text="SAP Series number used for this company's product catalog queries (e.g. 77).",
            ),
        ),
        # Drop the CompanySeries table (no longer needed)
        migrations.DeleteModel(
            name='CompanySeries',
        ),
    ]

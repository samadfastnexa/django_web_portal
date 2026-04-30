from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_ledger', '0004_ledgersettings_colors'),
    ]

    operations = [
        migrations.AddField(
            model_name='ledgersettings',
            name='font_size_group_name',
            field=models.PositiveSmallIntegerField(
                default=11,
                verbose_name='Font Size — Group Name',
                help_text='Font size (pt) for the group name in the PDF header.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='font_size_company_name',
            field=models.PositiveSmallIntegerField(
                default=13,
                verbose_name='Font Size — Company Name',
                help_text='Font size (pt) for the company name in the PDF header.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='font_size_report_title',
            field=models.PositiveSmallIntegerField(
                default=10,
                verbose_name='Font Size — Report Title',
                help_text='Font size (pt) for the report title line.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='font_size_dates',
            field=models.PositiveSmallIntegerField(
                default=9,
                verbose_name='Font Size — Date Range',
                help_text='Font size (pt) for the From/To date range line.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='font_size_table_header',
            field=models.PositiveSmallIntegerField(
                default=8,
                verbose_name='Font Size — Table Header Row',
                help_text='Font size (pt) for the table column-header row.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='font_size_table_data',
            field=models.PositiveSmallIntegerField(
                default=8,
                verbose_name='Font Size — Table Data Rows',
                help_text='Font size (pt) for table data rows.',
            ),
        ),
    ]

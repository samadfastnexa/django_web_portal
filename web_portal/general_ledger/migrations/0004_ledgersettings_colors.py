from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general_ledger', '0003_ledgersettings_footer_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='ledgersettings',
            name='report_title',
            field=models.CharField(
                default='General Ledger',
                max_length=200,
                verbose_name='Report Title',
                help_text='Title displayed in the PDF header (e.g. "General Ledger").',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='table_header_bg_color',
            field=models.CharField(
                default='#1e293b', max_length=20,
                verbose_name='Table Header Background Color',
                help_text='Hex color for the column-header row background (e.g. #1e293b).',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='table_header_text_color',
            field=models.CharField(
                default='#ffffff', max_length=20,
                verbose_name='Table Header Text Color',
                help_text='Hex color for the column-header text (e.g. #ffffff).',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='territory_row_bg_color',
            field=models.CharField(
                default='#f1f5f9', max_length=20,
                verbose_name='Territory Row Background Color',
                help_text='Hex color for territory grouping row background.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='closing_balance_bg_color',
            field=models.CharField(
                default='#f1f5f9', max_length=20,
                verbose_name='Closing Balance Row Background Color',
                help_text='Hex color for the per-BP closing balance row.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='grand_total_bg_color',
            field=models.CharField(
                default='#e2e8f0', max_length=20,
                verbose_name='Grand Total Row Background Color',
                help_text='Hex color for the grand total row.',
            ),
        ),
        migrations.AddField(
            model_name='ledgersettings',
            name='grid_color',
            field=models.CharField(
                default='#d1d5db', max_length=20,
                verbose_name='Grid / Border Color',
                help_text='Hex color for table grid lines.',
            ),
        ),
    ]

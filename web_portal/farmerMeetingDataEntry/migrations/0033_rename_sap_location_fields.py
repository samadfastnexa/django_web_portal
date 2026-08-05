"""Drop the sap_ prefix from the meeting location columns.

RenameField, not remove-and-add: makemigrations proposes the latter when run
non-interactively, and that would drop every value already recorded.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farmerMeetingDataEntry', '0032_alter_meeting_sap_region_alter_meeting_sap_territory_and_more'),
    ]

    operations = [
        migrations.RenameField(model_name='meeting', old_name='sap_employee_code', new_name='employee_code'),
        migrations.RenameField(model_name='meeting', old_name='sap_region', new_name='region'),
        migrations.RenameField(model_name='meeting', old_name='sap_zone', new_name='zone'),
        migrations.RenameField(model_name='meeting', old_name='sap_territory', new_name='territory'),
        migrations.RenameField(model_name='meeting', old_name='sap_territory_id', new_name='territory_code'),
        migrations.AlterField(
            model_name='meeting',
            name='employee_code',
            field=models.CharField(blank=True, db_index=True, help_text='Employee code the location below was resolved from', max_length=50, null=True, verbose_name='Employee code'),
        ),
        migrations.AlterField(
            model_name='meeting',
            name='region',
            field=models.TextField(blank=True, help_text='Region(s) assigned to the employee, comma separated.', null=True, verbose_name='Region'),
        ),
        migrations.AlterField(
            model_name='meeting',
            name='zone',
            field=models.TextField(blank=True, help_text='Zone(s) assigned to the employee, comma separated.', null=True, verbose_name='Zone'),
        ),
        migrations.AlterField(
            model_name='meeting',
            name='territory',
            field=models.TextField(blank=True, help_text='Territory/territories assigned to the employee, comma separated. Narrows to the single one when the meeting names it via territory_code.', null=True, verbose_name='Territory'),
        ),
        migrations.AlterField(
            model_name='meeting',
            name='territory_code',
            field=models.IntegerField(blank=True, db_index=True, help_text='SAP OTER.territryID - set only when one territory applies, either because the employee has just one or because the meeting named it.', null=True, verbose_name='Territory code'),
        ),
    ]

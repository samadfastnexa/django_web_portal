from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farmerMeetingDataEntry', '0025_alter_hpmrequisition_meeting_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='fieldday',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='meeting',
            options={
                'ordering': ['-created_at', '-id'],
                'verbose_name': 'Farmer Advisory Meeting',
                'verbose_name_plural': 'Farmer Advisory Meetings',
            },
        ),
        migrations.AlterModelOptions(
            name='fieldday',
            options={
                'ordering': ['-created_at', '-id'],
                'verbose_name': 'Field Day',
                'verbose_name_plural': 'Field Days',
            },
        ),
        migrations.AlterModelOptions(
            name='hpmrequisition',
            options={
                'ordering': ['-created_at', '-id'],
                'verbose_name': 'HPM Requisition',
                'verbose_name_plural': 'HPM Requisitions',
            },
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('FieldAdvisoryService', '0044_merge_20260428_1710'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetingschedule',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterModelOptions(
            name='meetingschedule',
            options={
                'ordering': ['-created_at', '-id'],
                'verbose_name': 'Field Advisory Meeting',
                'verbose_name_plural': 'Field Advisory Meetings',
            },
        ),
    ]

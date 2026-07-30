"""Introduce editable LeaveType / LeaveQuota and seed them from existing data.

The LeaveRequest.leave_type CharField is swapped to a ForeignKey without losing
any rows: a nullable FK is added, populated by matching the old code, and only
then does the old column go and the new one take its name.
"""
import django.db.models.deletion
from django.db import migrations, models

BUILTIN_TYPES = [
    # code, name, sort_order, legacy quota column on SalesStaffProfile
    ('sick', 'Sick', 1, 'sick_leave_quota'),
    ('casual', 'Casual', 2, 'casual_leave_quota'),
    ('other', 'Other', 3, 'others_leave_quota'),
]


def seed(apps, schema_editor):
    LeaveType = apps.get_model('attendance', 'LeaveType')
    LeaveRequest = apps.get_model('attendance', 'LeaveRequest')

    for code, name, order, _ in BUILTIN_TYPES:
        LeaveType.objects.get_or_create(
            code=code,
            defaults={'name': name, 'sort_order': order, 'is_active': True},
        )

    # Any code already in use but not in the builtin list (defensive: bad data
    # should not block the migration or lose its rows).
    existing = set(
        LeaveRequest.objects.exclude(leave_type_old__isnull=True)
        .exclude(leave_type_old='')
        .values_list('leave_type_old', flat=True)
        .distinct()
    )
    for code in existing - {c for c, _, _, _ in BUILTIN_TYPES}:
        LeaveType.objects.get_or_create(
            code=code[:20],
            defaults={'name': str(code).title()[:50], 'sort_order': 99, 'is_active': True},
        )

    by_code = {t.code: t for t in LeaveType.objects.all()}
    for request in LeaveRequest.objects.all():
        leave_type = by_code.get(request.leave_type_old)
        if leave_type is None:
            leave_type = by_code.get('other')
        request.leave_type = leave_type
        request.save(update_fields=['leave_type'])


def unseed(apps, schema_editor):
    LeaveRequest = apps.get_model('attendance', 'LeaveRequest')
    for request in LeaveRequest.objects.select_related('leave_type'):
        request.leave_type_old = request.leave_type.code if request.leave_type_id else ''
        request.save(update_fields=['leave_type_old'])


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0016_leaverequest_end_time_leaverequest_start_time'),
        ('accounts', '0031_alter_user_profile_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('code', models.SlugField(
                    help_text="Stable identifier used by the API, e.g. 'sick'. Avoid renaming.",
                    max_length=20, unique=True)),
                ('name', models.CharField(help_text="Label shown to users, e.g. 'Sick'.",
                                          max_length=50)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('default_quota', models.PositiveIntegerField(
                    default=0,
                    help_text='Days allowed when a staff member has no specific quota for this type.')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Leave type',
                'verbose_name_plural': 'Leave types',
                'db_table': 'attendance_leavetype',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LeaveQuota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('days', models.PositiveIntegerField(default=0)),
                ('leave_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='quotas', to='attendance.leavetype')),
                ('profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='leave_quotas', to='accounts.salesstaffprofile')),
            ],
            options={
                'verbose_name': 'Leave quota',
                'verbose_name_plural': 'Leave quotas',
                'db_table': 'attendance_leavequota',
                'unique_together': {('profile', 'leave_type')},
            },
        ),
        # Keep the old values under a temporary name while the FK is filled in.
        migrations.RenameField(
            model_name='leaverequest', old_name='leave_type', new_name='leave_type_old',
        ),
        migrations.AddField(
            model_name='leaverequest',
            name='leave_type',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='requests', to='attendance.leavetype'),
        ),
        migrations.RunPython(seed, unseed),
        migrations.RemoveField(model_name='leaverequest', name='leave_type_old'),
        migrations.AlterField(
            model_name='leaverequest',
            name='leave_type',
            field=models.ForeignKey(
                help_text='Managed under Attendance > Leave types.',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='requests', to='attendance.leavetype'),
        ),
    ]

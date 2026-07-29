"""Seed the admin-editable Attendance Report colour theme.

Creates the preferences.Setting row so the palette is visible and editable
under Settings in the admin instead of only existing in settings.py.
"""
from django.db import migrations

SLUG = 'attendance_report_colors'

DEFAULT_COLORS = {
    'title_bg': '#F2F2F2',
    'title_fg': '#000000',
    'date_bg': '#E2EFDA',
    'date_fg': '#000000',
    'header_bg': '#FFFF00',
    'header_fg': '#000000',
    'header_alt_bg': '#FCE4D6',
    'header_alt_fg': '#000000',
    'row_bg': '#FFFFFF',
    'row_alt_bg': '#F7F7F7',
    'row_fg': '#000000',
    'grid': '#808080',
}


def create_setting(apps, schema_editor):
    Setting = apps.get_model('preferences', 'Setting')
    Setting.objects.get_or_create(
        slug=SLUG,
        user=None,
        defaults={'value': dict(DEFAULT_COLORS), 'is_active': True},
    )


def delete_setting(apps, schema_editor):
    Setting = apps.get_model('preferences', 'Setting')
    Setting.objects.filter(slug=SLUG, user=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0014_fix_table_names_lowercase'),
        ('preferences', '0005_fix_table_names_lowercase'),
    ]

    operations = [
        migrations.RunPython(create_setting, delete_setting),
    ]

from django.db import migrations


def add_permission(apps, schema_editor):
    """Create reports.generate_report.

    accounts/0014 walks permissions_config.py, but it ran before this app
    existed, so the reports entry needs creating here. Same get_or_create
    shape, so both are safe to run in any order.
    """
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    Report = apps.get_model("reports", "Report")
    content_type = ContentType.objects.get_for_model(Report)
    Permission.objects.get_or_create(
        codename="generate_report",
        content_type=content_type,
        defaults={"name": "Can open Generate Report and run reports"},
    )


def remove_permission(apps, schema_editor):
    from django.contrib.auth.models import Permission

    Permission.objects.filter(
        codename="generate_report", content_type__app_label="reports"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0004_alter_branchaccess_options_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(add_permission, remove_permission)]

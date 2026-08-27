from django.db import migrations


def create_salesregister_report(apps, schema_editor):
    Report = apps.get_model("reports", "Report")
    Report.objects.get_or_create(
        name="SalesRegister",
        defaults={
            "display_name": "Sales Register",
            "description": "Sales register report, scoped by branch and sales employee.",
            "default_format": "pdf",
            "is_active": True,
        },
    )


def delete_salesregister_report(apps, schema_editor):
    Report = apps.get_model("reports", "Report")
    Report.objects.filter(name="SalesRegister").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_salesregister_report, delete_salesregister_report),
    ]

from django.db import migrations

# name must match the .rpt filename on the Crystal service, which only accepts
# [A-Za-z0-9_-] - hence the slug form of each report's display name.
REPORTS = [
    ("ProductLedgerWithSummary", "Product Ledger with Summary"),
    ("CustomerDetailLedgerWithSummary", "Customer Detail Ledger with Summary"),
    ("4bGeneralLedger", "4b General Ledger"),
    ("CollectionDetailReport", "Collection Detail Report"),
    ("BusinessHistory", "Business History"),
]


def create_reports(apps, schema_editor):
    Report = apps.get_model("reports", "Report")
    for name, display_name in REPORTS:
        Report.objects.get_or_create(
            name=name,
            defaults={
                "display_name": display_name,
                "default_format": "pdf",
                "is_active": True,
            },
        )


def delete_reports(apps, schema_editor):
    Report = apps.get_model("reports", "Report")
    Report.objects.filter(name__in=[name for name, _ in REPORTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0002_seed_salesregister_report"),
    ]

    operations = [
        migrations.RunPython(create_reports, delete_reports),
    ]

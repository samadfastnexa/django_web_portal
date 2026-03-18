from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from FieldAdvisoryService.models import Company, Region, Zone, Territory


class Command(BaseCommand):
    help = "Import predefined Region/Zone/Territory data for orange_live companies"

    def add_arguments(self, parser):
        parser.add_argument("--company-names", nargs="+", default=["4B-ORANG_APP"],
                          help="Company names to import data for")
        parser.add_argument("--dry-run", action="store_true", help="Validate without inserting")

    def handle(self, *args, **options):
        company_names = options["company_names"]
        dry_run = options.get("dry_run", False)

        # Data structure from the provided image
        territory_data = [
            {"region": "Eastern Hawks", "zone": "GUJRANWALA", "territory": "GUJRANWALA"},
            {"region": "Eastern Hawks", "zone": "SARGODHA", "territory": "SARGODHA"},
            {"region": "Eastern Hawks", "zone": "MIANWALI", "territory": "MIANWALI"},
            {"region": "Eastern Hawks", "zone": "KHUSHAB", "territory": "KHUSHAB"},
            {"region": "Eastern Hawks", "zone": "BHAKKAR", "territory": "BHAKKAR"},
            {"region": "Eastern Hawks", "zone": "LAYLLPUR", "territory": "LAYLLPUR"},
            {"region": "Eastern Hawks", "zone": "TOBA TEK SINGH", "territory": "TOBA TEK SINGH"},
            {"region": "Eastern Hawks", "zone": "MULTAN", "territory": "MULTAN"},
            {"region": "Eastern Hawks", "zone": "PAKPATTAN", "territory": "PAKPATTAN"},
            {"region": "Eastern Hawks", "zone": "SAHIWAL", "territory": "SAHIWAL"},
            {"region": "Northern Eagles", "zone": "GUJRANWALA", "territory": "GUJRANWALA"},
            {"region": "Northern Eagles", "zone": "SARGODHA", "territory": "SARGODHA"},
            {"region": "Northern Eagles", "zone": "MIANWALI", "territory": "MIANWALI"},
            {"region": "Northern Eagles", "zone": "KHUSHAB", "territory": "KHUSHAB"},
            {"region": "Northern Eagles", "zone": "BHAKKAR", "territory": "BHAKKAR"},
            {"region": "Central Tigers", "zone": "LAYLLPUR", "territory": "LAYLLPUR"},
            {"region": "Central Tigers", "zone": "TOBA TEK SINGH", "territory": "TOBA TEK SINGH"},
            {"region": "Central Tigers", "zone": "MULTAN", "territory": "MULTAN"},
            {"region": "Central Tigers", "zone": "PAKPATTAN", "territory": "PAKPATTAN"},
            {"region": "Central Tigers", "zone": "SAHIWAL", "territory": "SAHIWAL"},
            {"region": "Southern Lions", "zone": "BAHAWALPUR", "territory": "BAHAWALPUR"},
            {"region": "Southern Lions", "zone": "RAHIMYAR KHAN", "territory": "RAHIMYAR KHAN"},
            {"region": "Southern Lions", "zone": "MUZAFFARGARH", "territory": "MUZAFFARGARH"},
            {"region": "Southern Lions", "zone": "LAYYAH", "territory": "LAYYAH"},
            {"region": "Southern Lions", "zone": "DG KHAN", "territory": "DG KHAN"},
            {"region": "Atlantic Rhinos", "zone": "OKARA", "territory": "OKARA"},
            {"region": "Atlantic Rhinos", "zone": "KASUR", "territory": "KASUR"},
            {"region": "Atlantic Rhinos", "zone": "SHEIKHUPURA", "territory": "SHEIKHUPURA"},
            {"region": "Atlantic Rhinos", "zone": "NANKANA SAHIB", "territory": "NANKANA SAHIB"},
            {"region": "Atlantic Rhinos", "zone": "CHINIOT", "territory": "CHINIOT"},
            {"region": "GREEN-1", "zone": "VEHARI", "territory": "VEHARI"},
            {"region": "GREEN-1", "zone": "LODHRAN", "territory": "LODHRAN"},
            {"region": "GREEN-1", "zone": "KHANEWAL", "territory": "KHANEWAL"},
            {"region": "GREEN-2", "zone": "T.T SINGH", "territory": "T.T SINGH"},
            {"region": "GREEN-2", "zone": "JHANG", "territory": "JHANG"},
            {"region": "GREEN-2", "zone": "HAFIZABAD", "territory": "HAFIZABAD"},
            {"region": "WHITE-1", "zone": "MANDI BAHAUDDIN", "territory": "MANDI BAHAUDDIN"},
            {"region": "WHITE-1", "zone": "SIALKOT", "territory": "SIALKOT"},
            {"region": "WHITE-1", "zone": "NAROWAL", "territory": "NAROWAL"},
            {"region": "WHITE-2", "zone": "GUJRAT", "territory": "GUJRAT"},
            {"region": "WHITE-2", "zone": "JHELUM", "territory": "JHELUM"},
            {"region": "WHITE-2", "zone": "CHAKWAL", "territory": "CHAKWAL"},
            {"region": "BALUCHISTAN", "zone": "QUETTA", "territory": "QUETTA"},
            {"region": "BALUCHISTAN", "zone": "PISHIN", "territory": "PISHIN"},
            {"region": "BALUCHISTAN", "zone": "CHAMAN", "territory": "CHAMAN"},
        ]

        report = {
            "companies_processed": 0,
            "regions_created": 0,
            "zones_created": 0,
            "territories_created": 0,
            "duplicates_skipped": 0,
            "errors": []
        }

        for company_name in company_names:
            try:
                company = Company.objects.get(Company_name=company_name)
            except Company.DoesNotExist:
                report["errors"].append(f"Company '{company_name}' not found")
                continue

            report["companies_processed"] += 1

            with transaction.atomic():
                for item in territory_data:
                    region_name = item["region"]
                    zone_name = item["zone"]
                    territory_name = item["territory"]

                    # Create or get Region
                    region, region_created = Region.objects.get_or_create(
                        name=region_name,
                        company=company
                    )
                    if region_created and not dry_run:
                        report["regions_created"] += 1

                    # Create or get Zone
                    zone, zone_created = Zone.objects.get_or_create(
                        name=zone_name,
                        company=company,
                        region=region
                    )
                    if zone_created and not dry_run:
                        report["zones_created"] += 1

                    # Create Territory if it doesn't exist
                    territory_exists = Territory.objects.filter(
                        name=territory_name,
                        zone=zone,
                        company=company
                    ).exists()

                    if territory_exists:
                        report["duplicates_skipped"] += 1
                    elif not dry_run:
                        Territory.objects.create(
                            name=territory_name,
                            zone=zone,
                            company=company
                        )
                        report["territories_created"] += 1
                    elif dry_run:
                        report["territories_created"] += 1

            self.stdout.write(
                self.style.SUCCESS(f"✓ Processed company: {company.Company_name}")
            )

        # Print summary report
        self.stdout.write("\n" + "="*60)
        self.stdout.write("IMPORT SUMMARY REPORT")
        self.stdout.write("="*60)
        self.stdout.write(f"Companies processed: {report['companies_processed']}")
        self.stdout.write(f"Regions created: {report['regions_created']}")
        self.stdout.write(f"Zones created: {report['zones_created']}")
        self.stdout.write(f"Territories created: {report['territories_created']}")
        self.stdout.write(f"Duplicates skipped: {report['duplicates_skipped']}")

        if report["errors"]:
            self.stdout.write(f"Errors: {len(report['errors'])}")
            for error in report["errors"]:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n*** DRY RUN MODE - No changes were made ***"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✓ Import completed successfully!"))
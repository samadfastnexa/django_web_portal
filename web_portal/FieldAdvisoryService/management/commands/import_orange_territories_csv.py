import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from FieldAdvisoryService.models import Company, Region, Zone, Territory


class Command(BaseCommand):
    help = "Import regions, zones, and territories from CSV for 4B-ORANG_APP company"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            required=True,
            help="Path to CSV file with columns: Region,Zone,Territory"
        )
        parser.add_argument(
            "--company-id",
            type=int,
            help="Company ID (defaults to 4B-ORANG_APP lookup)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without inserting"
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing regions/zones/territories for this company before importing"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        company_id = options.get("company_id")
        dry_run = options.get("dry_run", False)
        clear_existing = options.get("clear_existing", False)

        # Resolve company
        company = self._resolve_company(company_id)
        if not company:
            raise CommandError("Company not found. Please specify --company-id or ensure 4B-ORANG_APP exists.")

        print("=" * 70)
        print(f"Importing territories for: {company.Company_name} (ID: {company.id})")
        print(f"CSV File: {csv_file}")
        print(f"Dry Run: {dry_run}")
        print(f"Clear Existing: {clear_existing}")
        print("=" * 70)

        # Clear existing data if requested
        if clear_existing and not dry_run:
            with transaction.atomic():
                deleted_territories = Territory.objects.filter(company=company).delete()[0]
                deleted_zones = Zone.objects.filter(company=company).delete()[0]
                deleted_regions = Region.objects.filter(company=company).delete()[0]
                print(f"\n[CLEARED] {deleted_regions} regions, {deleted_zones} zones, {deleted_territories} territories\n")

        # Read CSV
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_file}")
        except Exception as e:
            raise CommandError(f"Error reading CSV file: {e}")

        if not rows:
            raise CommandError("CSV file is empty or invalid")

        # Validate CSV headers
        required_headers = {'Region', 'Zone', 'Territory'}
        if not required_headers.issubset(set(rows[0].keys())):
            raise CommandError(f"CSV must have headers: {required_headers}")

        # Process rows
        report = {
            "total_rows": len(rows),
            "inserted_regions": 0,
            "inserted_zones": 0,
            "inserted_territories": 0,
            "duplicate_regions": 0,
            "duplicate_zones": 0,
            "duplicate_territories": 0,
            "errors": [],
        }

        with transaction.atomic():
            for idx, row in enumerate(rows, start=1):
                region_name = (row.get("Region") or "").strip()
                zone_name = (row.get("Zone") or "").strip()
                territory_name = (row.get("Territory") or "").strip()

                if not region_name or not zone_name or not territory_name:
                    report["errors"].append(f"Row {idx}: Missing region/zone/territory name")
                    continue

                try:
                    # Create or get Region
                    region_obj, region_created = Region.objects.get_or_create(
                        name=region_name,
                        company=company,
                        defaults={'created_by': None}
                    )
                    if region_created:
                        report["inserted_regions"] += 1
                        if not dry_run:
                            print(f"  [+] Region: {region_name}")
                    else:
                        report["duplicate_regions"] += 1

                    # Create or get Zone
                    zone_obj, zone_created = Zone.objects.get_or_create(
                        name=zone_name,
                        company=company,
                        region=region_obj,
                        defaults={'created_by': None}
                    )
                    if zone_created:
                        report["inserted_zones"] += 1
                        if not dry_run:
                            print(f"    [+] Zone: {zone_name}")
                    else:
                        report["duplicate_zones"] += 1

                    # Create or get Territory
                    territory_obj, territory_created = Territory.objects.get_or_create(
                        name=territory_name,
                        zone=zone_obj,
                        company=company,
                        defaults={'created_by': None, 'latitude': None, 'longitude': None}
                    )
                    if territory_created:
                        report["inserted_territories"] += 1
                        if not dry_run:
                            print(f"      [+] Territory: {territory_name}")
                    else:
                        report["duplicate_territories"] += 1

                except Exception as ex:
                    error_msg = f"Row {idx} ({region_name}/{zone_name}/{territory_name}): {ex}"
                    report["errors"].append(error_msg)
                    print(f"  [ERROR] {error_msg}")

            if dry_run:
                # Rollback transaction in dry-run mode
                transaction.set_rollback(True)

        # Print report
        self._print_report(report, company, dry_run)

    def _resolve_company(self, company_id):
        """Resolve company by ID or lookup 4B-ORANG_APP"""
        if company_id:
            try:
                return Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return None

        # Try to find 4B-ORANG_APP
        name_options = ["4B-ORANG_APP", "4B-ORANG-APP", "4B_ORANG_APP", "4B ORANG APP"]
        for name in name_options:
            try:
                return Company.objects.get(name=name)
            except Company.DoesNotExist:
                pass
            try:
                return Company.objects.get(Company_name=name)
            except Company.DoesNotExist:
                pass

        return None

    def _print_report(self, report, company, dry_run):
        """Print import report"""
        print("\n" + "=" * 70)
        print(f"Import Report - Company: {company.Company_name}")
        print("=" * 70)
        print(f"Total rows processed:          {report['total_rows']}")
        print(f"Regions inserted:              {report['inserted_regions']}")
        print(f"Zones inserted:                {report['inserted_zones']}")
        print(f"Territories inserted:          {report['inserted_territories']}")
        print(f"Duplicate regions (skipped):   {report['duplicate_regions']}")
        print(f"Duplicate zones (skipped):     {report['duplicate_zones']}")
        print(f"Duplicate territories (skip):  {report['duplicate_territories']}")
        print(f"Errors:                        {len(report['errors'])}")

        if report["errors"]:
            print("\nErrors:")
            for error in report["errors"]:
                print(f"  - {error}")

        if dry_run:
            print("\n[DRY RUN] No changes were made to the database.")

        print("=" * 70)

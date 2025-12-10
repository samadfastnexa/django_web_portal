import json
import logging
import re
from typing import List, Dict, Any, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from FieldAdvisoryService.models import Territory, Zone, Company


logger = logging.getLogger("seed_territories")


def validate_name(name: str) -> Tuple[bool, str]:
    if not isinstance(name, str):
        return False, "name must be a string"
    s = name.strip()
    if not s:
        return False, "name cannot be empty"
    if len(s) < 3:
        return False, "name must be at least 3 characters"
    if len(s) > 100:
        return False, "name must be <= 100 characters"
    if not re.match(r"^[A-Za-z0-9\s&\-'/]+$", s):
        return False, "name contains invalid characters"
    return True, ""


def load_entries(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        items = data.get("territories") or []
    else:
        items = data
    if not isinstance(items, list):
        raise CommandError("Input JSON must be a list of territory objects or { 'territories': [...] }")
    return items


class Command(BaseCommand):
    help = "Seed territories with validation, duplicate handling, transaction safety, and rollback support"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Path to JSON file containing territory entries")
        parser.add_argument("--company", help="Default company name or ID to use when entries omit company")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without inserting")
        parser.add_argument("--rollback", action="store_true", help="Delete territories matching input entries")
        parser.add_argument("--commit", action="store_true", help="Execute changes; otherwise only validate unless --rollback")

    def _resolve_company(self, company_ref: Any) -> Company:
        if company_ref is None:
            raise CommandError("Company reference is required (provide in entries or via --company)")
        if isinstance(company_ref, int):
            try:
                return Company.objects.get(id=company_ref)
            except Company.DoesNotExist:
                raise CommandError(f"Company id {company_ref} not found")
        name = str(company_ref).strip()
        try:
            return Company.objects.get(name=name)
        except Company.DoesNotExist:
            raise CommandError(f"Company '{name}' not found")

    def _resolve_zone(self, zone_ref: Any, company: Company) -> Zone:
        if zone_ref is None:
            raise CommandError("Zone reference is required in each entry")
        if isinstance(zone_ref, int):
            try:
                z = Zone.objects.get(id=zone_ref)
            except Zone.DoesNotExist:
                raise CommandError(f"Zone id {zone_ref} not found")
            if z.company_id != company.id:
                raise CommandError(f"Zone id {zone_ref} does not belong to company '{company.name}'")
            return z
        name = str(zone_ref).strip()
        try:
            z = Zone.objects.get(name=name, company=company)
        except Zone.DoesNotExist:
            raise CommandError(f"Zone '{name}' not found for company '{company.name}'")
        return z

    def handle(self, *args, **options):
        path = options["path"]
        default_company_ref = options.get("company")
        dry_run = bool(options.get("dry_run"))
        rollback = bool(options.get("rollback"))
        commit = bool(options.get("commit"))

        entries = load_entries(path)

        report = {
            "total": len(entries),
            "validated": 0,
            "inserted": 0,
            "duplicates": 0,
            "skipped": 0,
            "deleted": 0,
            "errors": [],
            "items": [],
        }

        # First pass: validation
        validated_items = []
        for i, e in enumerate(entries, start=1):
            item_report = {"index": i, "name": None, "zone": None, "company": None, "status": ""}
            try:
                name = (e.get("name") or e.get("territory") or "").strip()
                ok, msg = validate_name(name)
                if not ok:
                    raise CommandError(f"Validation failed for name '{name}': {msg}")
                company_ref = e.get("company") or default_company_ref
                company = self._resolve_company(company_ref)
                zone_ref = e.get("zone")
                zone = self._resolve_zone(zone_ref, company)
                item_report.update({"name": name, "zone": zone.name, "company": company.name})
                # Duplicate check
                exists = Territory.objects.filter(name=name, zone=zone, company=company).exists()
                if exists:
                    item_report["status"] = "duplicate"
                    report["duplicates"] += 1
                else:
                    item_report["status"] = "valid"
                    validated_items.append({
                        "name": name,
                        "zone": zone,
                        "company": company,
                        "latitude": e.get("latitude"),
                        "longitude": e.get("longitude"),
                    })
                report["validated"] += 1
            except Exception as ex:
                err = f"Entry {i}: {ex}"
                logger.error(err)
                report["errors"].append(err)
                item_report["status"] = "error"
            finally:
                report["items"].append(item_report)

        if rollback:
            # Rollback: delete territories matching the input entries
            with transaction.atomic():
                for i, e in enumerate(entries, start=1):
                    try:
                        name = (e.get("name") or e.get("territory") or "").strip()
                        company_ref = e.get("company") or default_company_ref
                        company = self._resolve_company(company_ref)
                        zone_ref = e.get("zone")
                        zone = self._resolve_zone(zone_ref, company)
                        qs = Territory.objects.filter(name=name, zone=zone, company=company)
                        deleted_count, _ = qs.delete()
                        if deleted_count:
                            logger.info(f"Deleted territory '{name}' (zone '{zone.name}', company '{company.name}')")
                            report["deleted"] += deleted_count
                        else:
                            logger.info(f"No matching territory to delete for '{name}' (zone '{zone.name}', company '{company.name}')")
                    except Exception as ex:
                        err = f"Rollback entry {i}: {ex}"
                        logger.error(err)
                        report["errors"].append(err)
            self._print_report(report)
            return

        if dry_run and not commit:
            # Only validation/reporting
            self._print_report(report)
            return

        # Seed within a single transaction: all-or-nothing
        with transaction.atomic():
            for item in validated_items:
                try:
                    t = Territory(
                        name=item["name"],
                        zone=item["zone"],
                        company=item["company"],
                    )
                    lat = item.get("latitude")
                    lng = item.get("longitude")
                    if lat is not None:
                        t.latitude = lat
                    if lng is not None:
                        t.longitude = lng
                    t.save()
                    logger.info(f"Inserted territory '{t.name}' (zone '{t.zone.name}', company '{t.company.name}')")
                    report["inserted"] += 1
                except Exception as ex:
                    err = f"Insert failed for '{item['name']}': {ex}"
                    logger.error(err)
                    raise  # abort all inserts

        # Recompute skipped as duplicates
        report["skipped"] = report["duplicates"]
        self._print_report(report)

    def _print_report(self, report: Dict[str, Any]):
        print("============================================================")
        print("Territory Seed Report")
        print("============================================================")
        print(f"Total entries: {report['total']}")
        print(f"Validated:     {report['validated']}")
        print(f"Inserted:      {report['inserted']}")
        print(f"Skipped dupes: {report['skipped']}")
        print(f"Deleted:       {report['deleted']}")
        print(f"Errors:        {len(report['errors'])}")
        if report["errors"]:
            print("\nErrors:")
            for e in report["errors"]:
                print(f" - {e}")
        print("\nItems:")
        for it in report["items"]:
            name = it.get("name")
            zone = it.get("zone")
            company = it.get("company")
            status = it.get("status")
            print(f" - [{status}] {name} (zone='{zone}', company='{company}')")
        print("============================================================")


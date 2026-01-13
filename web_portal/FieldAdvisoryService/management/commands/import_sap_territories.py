import os
from typing import Any, Dict, List, Optional, Tuple
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from FieldAdvisoryService.models import Company, Region, Zone, Territory
from FieldAdvisoryService.views import get_hana_connection
from sap_integration.hana_connect import territories_all_full

class Command(BaseCommand):
    help = "Import territories from SAP HANA (list_territories_full) for specified company DBs"

    def add_arguments(self, parser):
        parser.add_argument("--company-dbs", nargs="+", default=["4B-BIO", "4B-ORANG"], help="Company DB identifiers to import from")
        parser.add_argument("--company-id", type=int, help="Company ID in Django to attach imported regions/zones/territories")
        parser.add_argument("--limit", type=int, default=10000, help="Limit number of HANA rows to fetch")
        parser.add_argument("--status", type=str, choices=["active", "inactive"], default=None, help="Optional status filter")
        parser.add_argument("--dry-run", action="store_true", help="Validate without inserting")

    def handle(self, *args, **options):
        company_dbs: List[str] = options["company_dbs"]
        company_id: Optional[int] = options.get("company_id")
        limit: int = int(options["limit"])
        status: Optional[str] = options.get("status") or None
        dry_run: bool = bool(options.get("dry_run"))

        company = self._resolve_company(company_id, company_dbs[0])
        if not company:
            raise CommandError("Company not found; provide --company-id")

        report = {
            "dbs": [],
            "inserted_regions": 0,
            "inserted_zones": 0,
            "inserted_territories": 0,
            "duplicates": 0,
            "errors": [],
        }

        for db_code in company_dbs:
            schema = self._map_schema(db_code)
            if not schema:
                report["errors"].append(f"Unsupported company_db '{db_code}'")
                continue
            os.environ["HANA_SCHEMA"] = schema
            db = get_hana_connection()
            if not db:
                report["errors"].append(f"Failed to connect HANA for '{db_code}'")
                continue
            try:
                rows = territories_all_full(db, limit=limit, status=status)
            except Exception as e:
                report["errors"].append(f"HANA query failed for '{db_code}': {e}")
                try:
                    db.close()
                except Exception:
                    pass
                continue

            by_id = {self._get_int(r.get("TERRITORYID")): r for r in rows if self._get_int(r.get("TERRITORYID")) is not None}
            parent_ids = set()
            for r in rows:
                pid = self._get_int(r.get("PARENTID"))
                if pid is not None:
                    parent_ids.add(pid)

            inserted_regions = 0
            inserted_zones = 0
            inserted_territories = 0
            duplicates = 0
            errors_local: List[str] = []

            # Treat leaf nodes (SAP Pockets). We will create Django Territories from their parent SAP Territory.
            leaves = [r for r in rows if (self._get_int(r.get("TERRITORYID")) not in parent_ids)]
            processed_territory_ids: set[int] = set()
            with transaction.atomic():
                for r in leaves:
                    tid = self._get_int(r.get("TERRITORYID"))  # Pocket id
                    parent_id = self._get_int(r.get("PARENTID"))  # SAP Territory id
                    if tid is None or parent_id is None:
                        continue
                    # Avoid duplicate inserts for multiple pockets under the same Territory
                    if parent_id in processed_territory_ids:
                        continue
                    # SAP Hierarchy: Region → Zone → Sub Zone → Territory → Pocket (5 levels)
                    # Django Model: Region → Zone → Territory (3 levels)
                    # For a leaf Pocket:
                    #   parent        = Territory
                    #   grandparent   = Sub Zone
                    #   great-grand   = Zone (desired Zone in Django)
                    #   top-level     = Region (desired Region in Django)
                    # Correct mapping: Django Zone = SAP Zone, Django Region = SAP Region
                    territory_row = by_id.get(parent_id) if parent_id is not None else None
                    sub_zone_row = by_id.get(self._get_int(territory_row.get("PARENTID")) if territory_row else None)
                    zone_row = by_id.get(self._get_int(sub_zone_row.get("PARENTID")) if sub_zone_row else None)
                    region_row = by_id.get(self._get_int(zone_row.get("PARENTID")) if zone_row else None)
                    # Some datasets include a Sub Region above Zone; climb one more level if present
                    top_region_row = by_id.get(self._get_int(region_row.get("PARENTID")) if region_row and region_row.get("PARENTID") is not None else None)
                    use_region_row = top_region_row or region_row
                    region_name = (use_region_row.get("TERRITORYNAME") or "Unassigned").strip() if use_region_row else "Unassigned"
                    zone_name = (zone_row.get("TERRITORYNAME") or "Unassigned").strip() if zone_row else "Unassigned"
                    territory_name = (territory_row.get("TERRITORYNAME") or "Unassigned").strip() if territory_row else "Unassigned"
                    # Remove trailing ' Territory' from the name (case-insensitive)
                    if territory_name.lower().endswith(" territory"):
                        territory_name = territory_name[: -len(" territory")].rstrip()
                    region_obj, region_created = Region.objects.get_or_create(name=region_name, company=company)
                    if region_created:
                        inserted_regions += 1
                    zone_obj, zone_created = Zone.objects.get_or_create(name=zone_name, company=company, region=region_obj)
                    if zone_created:
                        inserted_zones += 1
                    exists = Territory.objects.filter(name=territory_name, zone=zone_obj, company=company).exists()
                    if exists:
                        duplicates += 1
                        processed_territory_ids.add(parent_id)
                        continue
                    if dry_run:
                        inserted_territories += 1
                        processed_territory_ids.add(parent_id)
                        continue
                    try:
                        Territory.objects.create(name=territory_name, zone=zone_obj, company=company)
                        inserted_territories += 1
                        processed_territory_ids.add(parent_id)
                    except Exception as ex:
                        errors_local.append(f"Insert failed for '{territory_name}': {ex}")

            try:
                db.close()
            except Exception:
                pass

            report["dbs"].append({
                "company_db": db_code,
                "schema": schema,
                "regions": inserted_regions,
                "zones": inserted_zones,
                "territories": inserted_territories,
                "duplicates": duplicates,
                "errors": errors_local,
            })
            report["inserted_regions"] += inserted_regions
            report["inserted_zones"] += inserted_zones
            report["inserted_territories"] += inserted_territories
            report["duplicates"] += duplicates
            report["errors"].extend(errors_local)

        self._print_report(report, company)

    def _resolve_company(self, company_id: Optional[int], fallback_db_code: str) -> Optional[Company]:
        if company_id:
            try:
                return Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return None
        name_opts = [fallback_db_code, fallback_db_code.replace("_APP", ""), fallback_db_code.replace("-APP", ""), fallback_db_code.replace("_", " ").replace("-", " ")]
        for nm in name_opts:
            try:
                return Company.objects.get(name=nm)
            except Company.DoesNotExist:
                pass
            try:
                return Company.objects.get(Company_name=nm)
            except Company.DoesNotExist:
                pass
        return Company.objects.first()

    def _map_schema(self, company_db: str) -> Optional[str]:
        s = company_db.strip().upper()
        if s in ("4B-BIO", "4B_BIO", "4B BIO", "4B-BIO-APP", "4B-BIO_APP"):
            return "4B-BIO_APP"
        if s in ("4B-ORANG", "4B_ORANG", "4B ORANG", "4B-ORANG-APP", "4B-ORANG_APP"):
            return "4B-ORANG_APP"
        return None

    def _get_int(self, v: Any) -> Optional[int]:
        try:
            if v is None:
                return None
            return int(v)
        except Exception:
            return None

    def _print_report(self, report: Dict[str, Any], company: Company):
        print("============================================================")
        print(f"SAP Territories Import Report -> Company '{company.name}'")
        print("============================================================")
        for db in report["dbs"]:
            print(f"[{db['company_db']}] schema={db['schema']} regions={db['regions']} zones={db['zones']} territories={db['territories']} duplicates={db['duplicates']} errors={len(db['errors'])}")
        print("------------------------------------------------------------")
        print(f"Total regions inserted:    {report['inserted_regions']}")
        print(f"Total zones inserted:      {report['inserted_zones']}")
        print(f"Total territories inserted:{report['inserted_territories']}")
        print(f"Total duplicates skipped:  {report['duplicates']}")
        print(f"Errors:                    {len(report['errors'])}")
        if report["errors"]:
            for e in report["errors"]:
                print(f" - {e}")
        print("============================================================")

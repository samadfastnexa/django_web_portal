import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import django

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_portal.settings")
django.setup()

from FieldAdvisoryService.models import Company, Region, Zone, Territory
from FieldAdvisoryService.views import get_hana_connection
from sap_integration.hana_connect import territories_all_full


def get_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def clean_name(name: str) -> str:
    s = (name or "").strip()
    for suffix in (" Region", " Zone", " Territory"):
        if s.lower().endswith(suffix.lower()):
            s = s[: -len(suffix)].rstrip()
    return s


def build_hierarchy_rows(schema_name: str, limit: int = 50000):
    os.environ["HANA_SCHEMA"] = schema_name
    db = get_hana_connection()
    if not db:
        raise RuntimeError(f"Could not connect to HANA for schema {schema_name}")

    try:
        rows = territories_all_full(db, limit=limit, status=None)
    finally:
        try:
            db.close()
        except Exception:
            pass

    by_id: Dict[int, Dict[str, Any]] = {}
    parent_ids = set()

    for row in rows:
        tid = get_int(row.get("TERRITORYID"))
        pid = get_int(row.get("PARENTID"))
        if tid is not None:
            by_id[tid] = row
        if pid is not None:
            parent_ids.add(pid)

    leaves = [r for r in rows if get_int(r.get("TERRITORYID")) not in parent_ids]
    processed_parent_territories = set()

    triples = []
    seen = set()

    for leaf in leaves:
        territory_id = get_int(leaf.get("TERRITORYID"))
        parent_id = get_int(leaf.get("PARENTID"))
        if territory_id is None or parent_id is None:
            continue

        if parent_id in processed_parent_territories:
            continue

        territory_row = by_id.get(parent_id)
        sub_zone_row = by_id.get(get_int(territory_row.get("PARENTID")) if territory_row else None)
        zone_row = by_id.get(get_int(sub_zone_row.get("PARENTID")) if sub_zone_row else None)
        region_row = by_id.get(get_int(zone_row.get("PARENTID")) if zone_row else None)
        top_region_row = by_id.get(get_int(region_row.get("PARENTID")) if region_row else None)

        use_region_row = top_region_row or region_row

        region_name = clean_name((use_region_row or {}).get("TERRITORYNAME") or "Unassigned")
        zone_name = clean_name((zone_row or {}).get("TERRITORYNAME") or "Unassigned")
        territory_name = clean_name((territory_row or {}).get("TERRITORYNAME") or "Unassigned")

        key = (region_name, zone_name, territory_name)
        if key in seen:
            processed_parent_territories.add(parent_id)
            continue

        seen.add(key)
        triples.append(key)
        processed_parent_territories.add(parent_id)

    triples.sort(key=lambda x: (x[0], x[1], x[2]))
    return triples


def write_csv(csv_path: Path, triples):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Region", "Zone", "Territory"])
        writer.writerows(triples)


def import_to_db(company_name: str, triples):
    company = Company.objects.filter(name=company_name).first()
    if not company:
        company = Company.objects.filter(Company_name=company_name).first()
    if not company:
        raise RuntimeError(f"Company not found: {company_name}")

    created_regions = 0
    created_zones = 0
    created_territories = 0
    existing_territories = 0

    for region_name, zone_name, territory_name in triples:
        region_obj, region_created = Region.objects.get_or_create(
            company=company,
            name=region_name,
            defaults={"created_by": None},
        )
        if region_created:
            created_regions += 1

        zone_obj, zone_created = Zone.objects.get_or_create(
            company=company,
            region=region_obj,
            name=zone_name,
            defaults={"created_by": None},
        )
        if zone_created:
            created_zones += 1

        _, territory_created = Territory.objects.get_or_create(
            company=company,
            zone=zone_obj,
            name=territory_name,
            defaults={"created_by": None, "latitude": None, "longitude": None},
        )
        if territory_created:
            created_territories += 1
        else:
            existing_territories += 1

    final_regions = Region.objects.filter(company=company).count()
    final_zones = Zone.objects.filter(company=company).count()
    final_territories = Territory.objects.filter(company=company).count()

    return {
        "company_id": company.id,
        "company": company.name,
        "created_regions": created_regions,
        "created_zones": created_zones,
        "created_territories": created_territories,
        "existing_territories": existing_territories,
        "final_regions": final_regions,
        "final_zones": final_zones,
        "final_territories": final_territories,
    }


def main():
    schema = "4B-AGRI_LIVE"
    company = "4B-AGRI_LIVE"
    csv_path = BASE_DIR / "data" / "agri_live_region_zone_territory.csv"

    triples = build_hierarchy_rows(schema_name=schema, limit=50000)
    write_csv(csv_path, triples)
    report = import_to_db(company_name=company, triples=triples)

    print("CSV_CREATED", csv_path)
    print("CSV_ROWS", len(triples))
    print("IMPORT_REPORT", report)


if __name__ == "__main__":
    main()

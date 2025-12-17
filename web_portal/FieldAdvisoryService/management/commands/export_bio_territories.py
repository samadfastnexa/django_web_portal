import json
import os
from typing import Any, Dict, List, Optional
from django.core.management.base import BaseCommand
from FieldAdvisoryService.views import get_hana_connection
from sap_integration.hana_connect import territories_all_full

class Command(BaseCommand):
    help = "Export leaf territories from SAP HANA (4B-BIO_APP) for preview or later seeding"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=1000, help="Max rows to fetch from HANA")
        parser.add_argument("--status", type=str, choices=["active", "inactive"], default=None, help="Optional status filter")
        parser.add_argument("--write-file", type=str, help="Write JSON to the given file path")
        parser.add_argument("--show", type=int, default=10, help="Show first N entries in terminal")

    def handle(self, *args, **options):
        os.environ["HANA_SCHEMA"] = "4B-BIO_APP"
        limit = int(options["limit"])
        status = options.get("status") or None
        write_file = options.get("write_file")
        show_n = int(options.get("show") or 10)

        db = get_hana_connection()
        rows = territories_all_full(db, limit=limit, status=status)
        try:
            db.close()
        except Exception:
            pass

        parents: set[int] = set()
        by_id: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            tid = self._get_int(r.get("TERRITORYID"))
            pid = self._get_int(r.get("PARENTID"))
            if tid is not None:
                by_id[tid] = r
            if pid is not None and pid >= 0:
                parents.add(pid)

        leafs = [r for r in rows if (self._get_int(r.get("TERRITORYID")) not in parents)]
        export_items = []
        for r in leafs:
            name = (r.get("TERRITORYNAME") or "").strip()
            if not name:
                continue
            export_items.append({
                "name": name,
                "company": "4B-BIO_APP",
                "zone": "",
                "latitude": None,
                "longitude": None,
            })

        report = {
            "schema": "4B-BIO_APP",
            "companies": ["4B-BIO_APP", "4B-ORANG_APP"],
            "total_rows": len(rows),
            "leaf_territories": len(export_items),
        }

        print("============================================================")
        print("BIO Territories Export (preview)")
        print("============================================================")
        print(f"Schema: {report['schema']}")
        print(f"Companies: {', '.join(report['companies'])}")
        print(f"Total rows fetched: {report['total_rows']}")
        print(f"Leaf territories:   {report['leaf_territories']}")
        print("------------------------------------------------------------")
        for i, it in enumerate(export_items[:show_n], start=1):
            print(f"{i:03d}. {it['name']}")
        if write_file:
            with open(write_file, "w", encoding="utf-8") as f:
                json.dump({"meta": {"companies": report["companies"], "source_company_db": "4B-BIO_APP"}, "territories": export_items}, f, ensure_ascii=False, indent=2)
            print("------------------------------------------------------------")
            print(f"Wrote JSON file: {write_file}")
        print("============================================================")

    def _get_int(self, v: Any) -> Optional[int]:
        try:
            if v is None:
                return None
            return int(v)
        except Exception:
            return None

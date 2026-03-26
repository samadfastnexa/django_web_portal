import csv
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import django
from django.db import transaction
from django.db.models import Count

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_portal.settings")
django.setup()

from FieldAdvisoryService.models import Company, Region, Zone, Territory
from FieldAdvisoryService.views import get_hana_connection
from accounts.models import DesignationModel, Role, SalesStaffProfile, User
from sap_integration.hana_connect import territories_all_full


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(str(value).strip())
    except Exception:
        return None


def _clean_text(value: Any) -> str:
    return (str(value).strip() if value is not None else "")


def _row_get(row: Dict[str, Any], *keys: str) -> Any:
    """Case-insensitive dictionary getter for SAP result rows."""
    if not row:
        return None
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key in row:
            return row[key]
        v = lowered.get(str(key).lower())
        if v is not None:
            return v
    return None


def _normalize_name(value: str) -> str:
    s = _clean_text(value).upper()
    s = re.sub(r"\s+", " ", s)
    return s


def _remove_geo_suffix(value: str) -> str:
    s = _clean_text(value)
    for suffix in (" Region", " Zone", " Territory"):
        if s.lower().endswith(suffix.lower()):
            s = s[: -len(suffix)].rstrip()
    return s


def _safe_alpha(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z ]+", " ", _clean_text(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or fallback


def _safe_username(seed: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9._+-]", "", seed.lower())
    return out[:150] or "user"


def _phone_digits(value: str) -> str:
    return re.sub(r"[^0-9+]", "", _clean_text(value))


def _resolve_designation(raw_designation: str) -> DesignationModel:
    name = _clean_text(raw_designation) or "Farmer Service Manager"

    by_name = DesignationModel.objects.filter(name__iexact=name).first()
    if by_name:
        return by_name

    by_code = DesignationModel.objects.filter(code__iexact=name).first()
    if by_code:
        return by_code

    code = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")[:20] or "FSM"
    candidate = code
    i = 1
    while DesignationModel.objects.filter(code=candidate).exists():
        suffix = str(i)
        candidate = f"{code[: max(1, 20 - len(suffix))]}{suffix}"
        i += 1

    level = 10
    return DesignationModel.objects.create(
        code=candidate,
        name=name,
        level=level,
        is_active=True,
        description="Auto-created during AGRI sales staff import",
    )


def _fetch_sap_employees(schema: str) -> List[Dict[str, Any]]:
    os.environ["HANA_SCHEMA"] = schema
    db = get_hana_connection()
    if not db:
        raise RuntimeError(f"Failed to connect HANA for schema '{schema}'")

    try:
        cur = db.cursor()
        cur.execute(f'SET SCHEMA "{schema}"')
        cur.execute(
            '''
            SELECT
                "empID",
                "firstName",
                "middleName",
                "lastName",
                "email",
                "mobile",
                "homeTel",
                "officeExt",
                "jobTitle",
                "U_TERR",
                "U_HOD",
                "Active"
            FROM "OHEM"
            WHERE "Active" = 'Y'
            ORDER BY "empID"
            '''
        )

        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append(
                {
                    "emp_code": _clean_text(r[0]),
                    "first_name": _clean_text(r[1]),
                    "middle_name": _clean_text(r[2]),
                    "last_name": _clean_text(r[3]),
                    "email": _clean_text(r[4]).lower(),
                    "mobile": _clean_text(r[5]),
                    "home_tel": _clean_text(r[6]),
                    "work_phone": _clean_text(r[7]),
                    "designation": _clean_text(r[8]),
                    "u_terr": _clean_text(r[9]),
                    "u_hod": _clean_text(r[10]),
                    "active": _clean_text(r[11]),
                }
            )
        return result
    finally:
        try:
            db.close()
        except Exception:
            pass


def _fetch_oter_lookup(schema: str) -> Dict[str, Dict[str, Any]]:
    os.environ["HANA_SCHEMA"] = schema
    db = get_hana_connection()
    if not db:
        return {}

    try:
        rows = territories_all_full(db, limit=50000, status=None)
        lookup: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            tid = _to_int(_row_get(r, "TERRITORYID", "TerritoryId", "territryID", "territoryid"))
            if tid is not None:
                lookup[str(tid)] = {
                    "id": tid,
                    "name": _clean_text(_row_get(r, "TERRITORYNAME", "TerritoryName", "descript")),
                    "parent_id": _to_int(_row_get(r, "PARENTID", "ParentId", "parent")),
                }
        return lookup
    except Exception:
        return {}
    finally:
        try:
            db.close()
        except Exception:
            pass


def _build_geo_lookup(company: Company) -> Dict[str, Tuple[Region, Zone, Territory]]:
    geo: Dict[str, Tuple[Region, Zone, Territory]] = {}
    qs = Territory.objects.filter(company=company).select_related("zone", "zone__region")
    for t in qs:
        key = _normalize_name(_remove_geo_suffix(t.name))
        if key and key not in geo:
            geo[key] = (t.zone.region, t.zone, t)
    return geo


def _resolve_geo_from_oter(token: str, oter_lookup: Dict[str, Dict[str, Any]]) -> Tuple[str, str, str]:
    """Map SAP token (territory id or name) to region/zone/territory names."""
    raw = _clean_text(token)
    if not raw:
        return "", "", ""

    if not raw.isdigit() or raw not in oter_lookup:
        terr = _remove_geo_suffix(raw)
        terr = re.sub(r"\s+Pocket$", "", terr, flags=re.IGNORECASE).strip()
        return "", "", terr

    by_id = oter_lookup
    leaf = by_id.get(raw) or {}
    parent = by_id.get(str(leaf.get("parent_id"))) if leaf.get("parent_id") is not None else None
    grand = by_id.get(str(parent.get("parent_id"))) if parent and parent.get("parent_id") is not None else None
    great = by_id.get(str(grand.get("parent_id"))) if grand and grand.get("parent_id") is not None else None
    top = by_id.get(str(great.get("parent_id"))) if great and great.get("parent_id") is not None else None

    # Prefer parent as Django territory when U_TERR points to pocket; otherwise use leaf.
    territory_name = _remove_geo_suffix((parent or leaf).get("name") or "")
    zone_name = _remove_geo_suffix((great or grand or {}).get("name") or "")
    region_name = _remove_geo_suffix((top or great or {}).get("name") or "")

    territory_name = re.sub(r"\s+Pocket$", "", territory_name, flags=re.IGNORECASE).strip()
    return region_name, zone_name, territory_name


def create_csv(schema: str, company_name: str, csv_path: Path) -> Dict[str, Any]:
    company = Company.objects.filter(name=company_name).first() or Company.objects.filter(Company_name=company_name).first()
    if not company:
        raise RuntimeError(f"Company not found: {company_name}")

    sap_rows = _fetch_sap_employees(schema)
    oter_lookup = _fetch_oter_lookup(schema)
    geo_lookup = _build_geo_lookup(company)

    output_rows: List[Dict[str, str]] = []
    unresolved = 0

    for row in sap_rows:
        emp_code = row["emp_code"]
        first_name = _safe_alpha(row["first_name"], "Employee")
        middle_name = _safe_alpha(row["middle_name"], "")
        last_name = _safe_alpha(row["last_name"], emp_code or "Staff")

        employee_name = " ".join([p for p in [first_name, middle_name, last_name] if p]).strip()
        designation = row["designation"] or "Farmer Service Manager"
        email = row["email"]
        mobile = row["mobile"]
        work_phone = row["work_phone"] or row["home_tel"]

        raw_territory = row["u_terr"]
        region_name, zone_name, territory_name = _resolve_geo_from_oter(raw_territory, oter_lookup)

        mapped_region = ""
        mapped_zone = ""
        mapped_territory = ""

        geo_key = _normalize_name(territory_name)
        if geo_key and geo_key in geo_lookup:
            rg, zn, tr = geo_lookup[geo_key]
            mapped_region = rg.name
            mapped_zone = zn.name
            mapped_territory = tr.name
        else:
            unresolved += 1

        output_rows.append(
            {
                "EmpCode": emp_code,
                "EmployeeName": employee_name,
                "Designation": designation,
                "Region": mapped_region or region_name,
                "Zone": mapped_zone or zone_name,
                "Territory": mapped_territory or territory_name,
                "Company": company.name,
                "EmployeeCategory": "Sales",
                "WorkPhone": work_phone,
                "MobileNo": mobile,
                "Email": email,
                "SourceTerritory": raw_territory,
                "SourceHOD": row["u_hod"],
            }
        )

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "EmpCode",
        "EmployeeName",
        "Designation",
        "Region",
        "Zone",
        "Territory",
        "Company",
        "EmployeeCategory",
        "WorkPhone",
        "MobileNo",
        "Email",
        "SourceTerritory",
        "SourceHOD",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)

    return {
        "rows": len(output_rows),
        "unresolved_geo_rows": unresolved,
        "csv_path": str(csv_path),
    }


def _unique_email(base_email: str, emp_code: str, existing_user: Optional[User]) -> str:
    if base_email:
        owner = User.objects.filter(email__iexact=base_email).exclude(id=existing_user.id if existing_user else None).first()
        if not owner:
            return base_email

    local = f"agri_emp_{emp_code}".lower()
    candidate = f"{local}@4b.local"
    i = 1
    while User.objects.filter(email__iexact=candidate).exclude(id=existing_user.id if existing_user else None).exists():
        candidate = f"{local}_{i}@4b.local"
        i += 1
    return candidate


def _unique_username(base: str, existing_user: Optional[User]) -> str:
    candidate = _safe_username(base)
    i = 1
    while User.objects.filter(username__iexact=candidate).exclude(id=existing_user.id if existing_user else None).exists():
        suffix = str(i)
        trimmed = candidate[: max(1, 150 - len(suffix))]
        candidate = f"{trimmed}{suffix}"
        i += 1
    return candidate


def _safe_user_phone(raw_mobile: str, existing_user: Optional[User]) -> Optional[str]:
    phone = _phone_digits(raw_mobile)
    if not phone:
        return None
    phone = phone[:20]

    owner = User.objects.filter(phone_number=phone).exclude(id=existing_user.id if existing_user else None).first()
    if owner:
        return None
    return phone


def import_csv(csv_path: Path, company_name: str) -> Dict[str, Any]:
    company = Company.objects.filter(name=company_name).first() or Company.objects.filter(Company_name=company_name).first()
    if not company:
        raise RuntimeError(f"Company not found: {company_name}")

    role = Role.objects.filter(name="FirstRole").first() or Role.objects.first()

    created_users = 0
    updated_users = 0
    created_profiles = 0
    updated_profiles = 0
    rows_processed = 0
    rows_skipped = 0
    manager_links_set = 0
    geo_inherited_from_manager = 0

    rows_cache: List[Dict[str, str]] = []

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with transaction.atomic():
            for row in reader:
                rows_cache.append(row)
                emp_code = _clean_text(row.get("EmpCode"))
                if not emp_code:
                    rows_skipped += 1
                    continue

                rows_processed += 1

                full_name = _clean_text(row.get("EmployeeName"))
                parts = [p for p in full_name.split(" ") if p]
                first_name = _safe_alpha(parts[0] if parts else "Employee", "Employee")
                last_name = _safe_alpha(" ".join(parts[1:]) if len(parts) > 1 else emp_code, emp_code)

                designation_obj = _resolve_designation(_clean_text(row.get("Designation")))

                existing_profile = SalesStaffProfile.objects.filter(employee_code=emp_code).select_related("user").first()
                linked_user = existing_profile.user if existing_profile and existing_profile.user else None

                email = _unique_email(_clean_text(row.get("Email")).lower(), emp_code, linked_user)
                username_seed = email.split("@")[0] if "@" in email else f"agri_{emp_code}"
                username = _unique_username(username_seed, linked_user)
                user_phone = _safe_user_phone(_clean_text(row.get("MobileNo")), linked_user)

                if linked_user:
                    user = linked_user
                    user.first_name = first_name
                    user.last_name = last_name
                    user.email = email
                    user.username = username
                    user.is_active = True
                    user.is_sales_staff = True
                    if role and not user.role_id:
                        user.role = role
                    if user_phone:
                        user.phone_number = user_phone
                    user.company = company
                    user.save()
                    updated_users += 1
                else:
                    existing_by_email = User.objects.filter(email__iexact=email).first()
                    if existing_by_email:
                        user = existing_by_email
                        user.first_name = first_name
                        user.last_name = last_name
                        user.username = username
                        user.is_active = True
                        user.is_sales_staff = True
                        if role and not user.role_id:
                            user.role = role
                        if user_phone:
                            user.phone_number = user_phone
                        user.company = company
                        user.save()
                        updated_users += 1
                    else:
                        user = User.objects.create(
                            email=email,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            phone_number=user_phone,
                            company=company,
                            role=role,
                            is_active=True,
                            is_sales_staff=True,
                            is_dealer=False,
                            is_staff=False,
                        )
                        # Set unusable password for imported staff accounts.
                        user.set_unusable_password()
                        user.save(update_fields=["password"])
                        created_users += 1

                address = f"Imported from SAP schema {company.name}"
                profile_phone = _clean_text(row.get("MobileNo")) or _clean_text(row.get("WorkPhone")) or None
                if profile_phone:
                    profile_phone = profile_phone[:20]

                profile, profile_created = SalesStaffProfile.objects.update_or_create(
                    employee_code=emp_code,
                    defaults={
                        "user": user,
                        "phone_number": profile_phone,
                        "address": address,
                        "designation": designation_obj,
                        "is_vacant": False,
                    },
                )
                if profile_created:
                    created_profiles += 1
                else:
                    updated_profiles += 1

                profile.companies.add(company)

                region_name = _clean_text(row.get("Region"))
                zone_name = _clean_text(row.get("Zone"))
                territory_name = _clean_text(row.get("Territory"))

                if region_name:
                    rg = Region.objects.filter(company=company, name__iexact=region_name).first()
                    if rg:
                        profile.regions.add(rg)
                if zone_name:
                    zn = Zone.objects.filter(company=company, name__iexact=zone_name).first()
                    if zn:
                        profile.zones.add(zn)
                if territory_name:
                    tr = Territory.objects.filter(company=company, name__iexact=territory_name).first()
                    if tr:
                        profile.territories.add(tr)

            # Second pass: manager linking + fallback geo inheritance via SourceHOD.
            for row in rows_cache:
                emp_code = _clean_text(row.get("EmpCode"))
                if not emp_code:
                    continue

                profile = SalesStaffProfile.objects.filter(employee_code=emp_code).first()
                if not profile:
                    continue

                hod_raw = _clean_text(row.get("SourceHOD"))
                if not hod_raw:
                    continue

                m = re.search(r"\d+", hod_raw)
                if not m:
                    continue

                manager_emp_code = m.group(0)
                manager_profile = SalesStaffProfile.objects.filter(employee_code=manager_emp_code).first()
                if not manager_profile:
                    continue

                if profile.manager_id != manager_profile.id:
                    profile.manager = manager_profile
                    profile.save(update_fields=["manager"])
                    manager_links_set += 1

                had_geo_before = profile.territories.exists() and profile.zones.exists() and profile.regions.exists()

                if not profile.regions.exists():
                    profile.regions.add(*manager_profile.regions.all())
                if not profile.zones.exists():
                    profile.zones.add(*manager_profile.zones.all())
                if not profile.territories.exists():
                    profile.territories.add(*manager_profile.territories.all())

                has_geo_after = profile.territories.exists() and profile.zones.exists() and profile.regions.exists()
                if (not had_geo_before) and has_geo_after:
                    geo_inherited_from_manager += 1

    dup_profiles = SalesStaffProfile.objects.values("employee_code").annotate(c=Count("id")).filter(c__gt=1).count()

    return {
        "rows_processed": rows_processed,
        "rows_skipped": rows_skipped,
        "created_users": created_users,
        "updated_users": updated_users,
        "created_profiles": created_profiles,
        "updated_profiles": updated_profiles,
        "manager_links_set": manager_links_set,
        "geo_inherited_from_manager": geo_inherited_from_manager,
        "duplicate_employee_codes": dup_profiles,
    }


def main():
    schema = "4B-AGRI_LIVE"
    company_name = "4B-AGRI_LIVE"
    csv_path = BASE_DIR / "data" / "agri_live_sales_staff.csv"

    csv_report = create_csv(schema=schema, company_name=company_name, csv_path=csv_path)
    import_report = import_csv(csv_path=csv_path, company_name=company_name)

    print("CSV_REPORT", csv_report)
    print("IMPORT_REPORT", import_report)


if __name__ == "__main__":
    main()

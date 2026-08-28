"""Who may run what, and over whose data.

Two separate questions, deliberately kept apart:

  * which COMPANIES a user may run against  -> SalesStaffCompany rows
  * which CUSTOMERS/TERRITORIES they may see -> the SAP employee code on that
    same row, resolved through B4_EMP -> OTER exactly as the customer LOV does

Everything here fails closed. A user we cannot resolve to an employee code gets
an empty list and a reason, never the unscoped list - that is the whole point of
the module, and getting it wrong leaks another region's dealers.

Superusers are the one exception: they are unscoped by design.
"""

import logging

logger = logging.getLogger("reports")


def is_unscoped(user):
    """Superusers see every company and every customer."""
    return bool(getattr(user, "is_superuser", False))


def user_company_memberships(user):
    """Active (company, employee_code) rows for this user, ordered by company.

    Returns [] for a user with no sales profile - which is the correct answer,
    not an error: a back-office account simply has no SAP identity.
    """
    profile = getattr(user, "sales_profile", None)
    if profile is None:
        return []
    try:
        from accounts.models import SalesStaffCompany

        rows = (
            SalesStaffCompany.objects.filter(sales_profile=profile, is_active=True)
            .select_related("company")
            .order_by("company__name")
        )
        return [row for row in rows if row.company and row.company.is_active]
    except Exception:
        logger.exception("Could not read company memberships for user %s", getattr(user, "id", None))
        return []


def allowed_companies(user, all_companies):
    """Company schemas this user may run reports against.

    ``all_companies`` is the registry's ALLOWED_COMPANIES, used for superusers
    and as the validity filter for everyone else: a membership pointing at a
    schema the reporting service does not accept is dropped rather than offered.
    """
    if is_unscoped(user):
        return sorted(all_companies)
    schemas = []
    for row in user_company_memberships(user):
        schema = (row.company.name or "").strip()
        if schema and schema in all_companies and schema not in schemas:
            schemas.append(schema)
    return schemas


def employee_code_for(user, company_schema=None):
    """SAP employee code for this user, within a company when one is given.

    Per-company code first (the whole reason SalesStaffCompany exists - the same
    person has a different code in each company), then the profile-level code as
    a fallback for single-company staff.
    """
    if is_unscoped(user):
        return None  # unscoped: callers must not filter
    for row in user_company_memberships(user):
        if company_schema and (row.company.name or "").strip() != company_schema:
            continue
        code = (row.employee_code or "").strip()
        if code:
            return code
    profile = getattr(user, "sales_profile", None)
    return ((getattr(profile, "employee_code", "") or "").strip() or None) if profile else None


def scope_for(user, company_schema=None):
    """One call for a view: (employee_code, error_message).

    error_message is None when the caller may proceed. A non-superuser with no
    resolvable code gets a message aimed at the person reading it, not a stack
    trace - and the caller must return an empty list, never fall through.
    """
    if is_unscoped(user):
        return None, None
    code = employee_code_for(user, company_schema)
    if code:
        return code, None
    if not user_company_memberships(user):
        return None, (
            "Your account is not linked to a company in SAP, so there are no "
            "customers to show. Ask an administrator to add a company and "
            "employee code to your sales profile."
        )
    return None, (
        "Your account has a company but no SAP employee code"
        + (f" for {company_schema}" if company_schema else "")
        + ", so customers and territories cannot be looked up. Ask an "
        "administrator to set it on your sales profile."
    )


# ---------------------------------------------------------------------------
# SAP lookups. Kept here rather than in views so the fail-closed rule lives in
# one file: every function returns ([], reason) instead of raising, and never
# returns unscoped rows for a scoped user.
# ---------------------------------------------------------------------------

def _hana(company_schema):
    """Open a HANA connection with CURRENT_SCHEMA set to one company.

    general_ledger.utils is the helper that takes the schema by name and issues
    SET SCHEMA; the sap_integration one resolves through the session dropdown,
    which is exactly what must NOT happen here - the schema comes from the
    user's own membership, not from whatever they last picked in the header.
    """
    from general_ledger.utils import get_hana_connection

    return get_hana_connection(company_schema)


def customers_for(user, company_schema, search=None, limit=50):
    """Dealer/customer list this user may pick from, newest SAP data.

    Superuser -> the company's whole customer list. Everyone else -> only the
    dealers hanging off their employee's OTER subtree, which is the same rule
    /api/sap/customer-lov/ applies.
    """
    from sap_integration.hana_connect import customer_lov

    code, error = scope_for(user, company_schema)
    if error:
        return [], error
    try:
        conn = _hana(company_schema)
        if conn is None:
            return [], "Could not connect to SAP for this company."
        rows = customer_lov(conn, search=search, limit=limit, status="active",
                            employee_code=code) or []
    except Exception:
        logger.exception("customer LOV failed for company %s", company_schema)
        return [], "SAP did not return a customer list. Please try again."

    out = [
        {
            "code": (r.get("CardCode") or "").strip(),
            "name": (r.get("CardName") or "").strip(),
            "territory": (r.get("TerritoryName") or "").strip(),
        }
        for r in rows
        if (r.get("CardCode") or "").strip()
    ]
    if not out and code:
        return [], (
            "No customers are mapped to your SAP employee code in this company. "
            "This usually means the employee has no territory assigned in SAP."
        )
    return out, None


def geo_for(user, company_schema, level, search=None, limit=200):
    """Region / Zone / Territory names this user may filter by.

    Scoped users get only the part of the OTER tree beneath their own nodes;
    a superuser gets the full list from geo_options(). `level` is one of
    region / zone / territory.
    """
    from sap_integration.hana_connect import (
        geo_options,
        employee_territory_ids,
        territory_descendants,
    )

    key = (level or "").strip().lower()
    if key not in ("region", "zone", "territory"):
        return [], f"Unknown level '{level}'."

    code, error = scope_for(user, company_schema)
    if error:
        return [], error

    try:
        conn = _hana(company_schema)
        if conn is None:
            return [], "Could not connect to SAP for this company."
        rows = geo_options(conn) or []
        if code:
            # Restrict to the names appearing on the employee's own subtree.
            allowed_ids = set(territory_descendants(conn, employee_territory_ids(conn, code)))
            if not allowed_ids:
                return [], (
                    "Your SAP employee code has no territory assigned, so there "
                    "are no regions or territories to choose from."
                )
            rows = _restrict_geo(conn, rows, allowed_ids)
    except Exception:
        logger.exception("geo LOV failed for company %s level %s", company_schema, key)
        return [], "SAP did not return the territory list. Please try again."

    column = {"region": "Region", "zone": "Zone", "territory": "Territory"}[key]
    names = sorted({(r.get(column) or "").strip() for r in rows if (r.get(column) or "").strip()})
    if search:
        needle = search.strip().lower()
        names = [n for n in names if needle in n.lower()]
    return [{"code": n, "name": n} for n in names[:limit]], None


def _restrict_geo(conn, rows, allowed_ids):
    """Keep only geo_options() rows whose territory node is in `allowed_ids`.

    geo_options() returns names, not ids, so map the permitted ids back to their
    descriptions and match on that. Names repeat across companies but not within
    one, and this always runs against a single company schema.
    """
    from sap_integration.hana_connect import _fetch_all

    if not allowed_ids:
        return []
    ids = sorted(allowed_ids)
    allowed_names = set()
    # Chunked so a national manager's ~1500 nodes cannot blow the statement limit.
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        placeholders = ",".join(["?"] * len(chunk))
        found = _fetch_all(
            conn,
            'SELECT "descript" AS "D" FROM "OTER" WHERE "territryID" IN (%s)' % placeholders,
            tuple(chunk),
        )
        for row in (found or []):
            name = (row.get("D") or "").strip()
            if name:
                allowed_names.add(name)
                if name.endswith(" Territory"):
                    allowed_names.add(name[:-10])
    return [
        r for r in rows
        if (r.get("Territory") or "").strip() in allowed_names
        or (r.get("Zone") or "").strip() in allowed_names
        or (r.get("Region") or "").strip() in allowed_names
    ]

"""Show why /api/sap/customer-lov/ returns the dealers it returns.

Usage (from django_web_portal/):
    PYTHONUTF8=1 python check_dealer_scope.py <user_id> [schema]
    PYTHONUTF8=1 python check_dealer_scope.py emp=<employee_code> [schema]

    PYTHONUTF8=1 python check_dealer_scope.py 2246 4B-AGRI_LIVE
    PYTHONUTF8=1 python check_dealer_scope.py emp=2260 4B-AGRI_LIVE

Walks the exact chain the endpoint uses:
    portal user -> sales profile employee_code -> SAP B4_EMP territories
    -> full OTER subtree (region/zone/sub zone/territory/pocket) -> OCRD dealers

The emp= form skips the portal lookup, matching ?employee_code= on the API.
"""

# --- bootstrap: this script lives in <app>/scripts/, so locate the project ---
import os as _os
import sys as _sys
from pathlib import Path as _P

PROJECT_DIR = _P(__file__).resolve().parents[2]   # web_portal/ (holds manage.py)
REPO_DIR = PROJECT_DIR.parent                     # django_web_portal/ (holds .env)
if str(PROJECT_DIR) not in _sys.path:
    _sys.path.insert(0, str(PROJECT_DIR))
_os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
# --- end bootstrap ---

import os
import sys

import django

sys.path.insert(0, str(PROJECT_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import (  # noqa: E402
    _fetch_all, _load_env_file, customer_lov, employee_territory_ids, territory_descendants,
)

HERE = str(REPO_DIR)
_load_env_file(str(PROJECT_DIR / 'sap_integration' / '.env'))
_load_env_file(str(REPO_DIR / '.env'))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    target = sys.argv[1]
    schema = sys.argv[2] if len(sys.argv) > 2 else '4B-AGRI_LIVE'

    if target.lower().startswith('emp='):
        code = target.split('=', 1)[1].strip()
        print(f"[1] Employee code given directly: {code!r} (portal lookup skipped)")
        print("[2] Equivalent to ?employee_code=%s on the API" % code)
        if not code:
            print("    -> blank employee code.")
            return 1
    else:
        user_id = target
        from accounts.models import User
        user = User.objects.filter(id=user_id).first()
        print(f"[1] Portal user {user_id}: {user or 'NOT FOUND'}")
        if not user:
            return 1

        profile = getattr(user, 'sales_profile', None)
        if not profile:
            print("    -> no sales staff profile. Endpoint returns 400.")
            return 1
        code = (profile.employee_code or '').strip()
        print(f"[2] Sales profile {profile.id}, employee_code = {code!r}")
        if not code:
            print("    -> employee_code is blank. Endpoint returns 400. Set it in admin.")
            return 1

    from hdbcli import dbapi
    kwargs = {
        'address': os.environ.get('HANA_HOST'),
        'port': int(os.environ.get('HANA_PORT') or 30015),
        'user': os.environ.get('HANA_USER'),
        'password': os.environ.get('HANA_PASSWORD'),
    }
    if str(os.environ.get('HANA_ENCRYPT', '')).strip().lower() in ('true', '1', 'yes'):
        kwargs['encrypt'] = True
        kwargs['sslValidateCertificate'] = str(
            os.environ.get('HANA_SSL_VALIDATE', '')).strip().lower() in ('true', '1', 'yes')
    conn = dbapi.connect(**kwargs)
    cur = conn.cursor()
    cur.execute(f'SET SCHEMA "{schema}"')
    cur.close()
    print(f"[3] Connected to schema {schema}")

    try:
        emp = _fetch_all(conn, 'SELECT "empID","firstName","lastName" FROM OHEM WHERE "empID" = ?', (int(code),))
        if emp:
            print(f"    SAP employee: {emp[0]}")
    except Exception:
        pass

    roots = employee_territory_ids(conn, code)
    print(f"[4] B4_EMP territories for CODE={code}: {len(roots)} -> {roots[:20]}"
          f"{' ...' if len(roots) > 20 else ''}")
    if not roots:
        print("    -> employee is not assigned any territory in SAP. Endpoint returns 0 dealers.")
        print("    -> FIX IN SAP: assign this employee a territory (OHEM/@TUAH -> B4_EMP).")
        conn.close()
        return 1

    scope = territory_descendants(conn, roots)
    placeholders = ','.join(['?'] * len(scope))
    nodes = _fetch_all(
        conn,
        f'SELECT "territryID","descript","parent" FROM OTER WHERE "territryID" IN ({placeholders})',
        tuple(str(t) for t in scope),
    ) or []
    print(f"[5] Full OTER subtree: {len(scope)} node(s)")
    for n in sorted(nodes, key=lambda r: r['territryID']):
        cnt = _fetch_all(
            conn,
            'SELECT COUNT(*) AS N FROM OCRD WHERE "CardType"=\'C\' AND "validFor"=\'Y\' AND "Territory" = ?',
            (n['territryID'],),
        )[0]['N']
        flag = '  <-- deactivated in SAP (x prefix)' if str(n['descript']).startswith('x') else ''
        print(f"    {n['territryID']:>6}  {n['descript']:<34} parent={n['parent']:<6} active_dealers={cnt}{flag}")

    rows = customer_lov(conn, limit=20000, employee_code=code)
    print(f"[6] Dealers the endpoint will return: {len(rows)}")
    for r in rows[:15]:
        # CardName/TerritoryName are NULL for a few OCRD rows.
        print(f"    {r['CardCode'] or '':<12} {r['CardName'] or '(no name)':<40} {r['TerritoryName'] or ''}")
    if len(rows) > 15:
        print(f"    ... and {len(rows) - 15} more")

    if not rows:
        print("\n    -> The employee IS mapped in SAP, but no dealer sits anywhere in that")
        print("       subtree. This is SAP master data, not a portal bug. Either move the")
        print("       dealers onto this territory, or reassign the employee in SAP.")
        # Suggest the nearest ancestor that does have dealers.
        parent = nodes[0]['parent'] if nodes else None
        while parent not in (None, -1):
            up = _fetch_all(conn, 'SELECT "territryID","descript","parent" FROM OTER WHERE "territryID" = ?', (parent,))
            if not up:
                break
            sub = territory_descendants(conn, [up[0]['territryID']])
            ph = ','.join(['?'] * len(sub))
            n = _fetch_all(
                conn,
                f'SELECT COUNT(*) AS N FROM OCRD WHERE "CardType"=\'C\' AND "validFor"=\'Y\' AND "Territory" IN ({ph})',
                tuple(str(t) for t in sub),
            )[0]['N']
            if n:
                print(f"       Nearest ancestor with dealers: {up[0]['territryID']} "
                      f"'{up[0]['descript']}' ({n} dealers).")
                break
            parent = up[0]['parent']

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())

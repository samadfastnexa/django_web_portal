"""Find the rows behind "Staff Company Membership with this ... already exists".

Usage (from web_portal/):
    PYTHONUTF8=1 python accounts/scripts/find_duplicate_employee_codes.py

SalesStaffCompany has two unique_together constraints:
    ('sales_profile', 'company')   - one membership row per profile per company
    ('company', 'employee_code')   - an employee code is unique within a company

Saving a profile revalidates all of its membership rows, so a duplicate created
earlier (or imported) blocks the save even when the row was not touched. This
lists every conflicting group so the offending row can be corrected.
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

import django

django.setup()

from django.db.models import Count  # noqa: E402

from accounts.models import SalesStaffCompany  # noqa: E402


def show(rows, title):
    print(f"\n{title}")
    print("-" * len(title))
    if not rows:
        print("  none")
    return rows


def main():
    total = SalesStaffCompany.objects.count()
    print(f"Staff Company Membership rows: {total}")

    # ('company', 'employee_code')
    dup_codes = (SalesStaffCompany.objects
                 .exclude(employee_code__isnull=True)
                 .exclude(employee_code='')
                 .values('company_id', 'employee_code')
                 .annotate(n=Count('id'))
                 .filter(n__gt=1)
                 .order_by('-n'))
    show(dup_codes, "Same employee_code used twice inside one company")
    for d in dup_codes:
        rows = (SalesStaffCompany.objects
                .filter(company_id=d['company_id'], employee_code=d['employee_code'])
                .select_related('company', 'sales_profile', 'sales_profile__user'))
        first = rows[0]
        print(f"  company '{first.company}' code '{d['employee_code']}' x{d['n']}")
        for r in rows:
            user = getattr(r.sales_profile, 'user', None)
            print(f"     membership#{r.pk}  profile#{r.sales_profile_id}  {user or '(vacant)'}"
                  f"  primary={r.is_primary} active={r.is_active}")

    # ('sales_profile', 'company')
    dup_pairs = (SalesStaffCompany.objects
                 .values('sales_profile_id', 'company_id')
                 .annotate(n=Count('id'))
                 .filter(n__gt=1)
                 .order_by('-n'))
    show(dup_pairs, "Same profile linked to one company more than once")
    for d in dup_pairs:
        rows = (SalesStaffCompany.objects
                .filter(sales_profile_id=d['sales_profile_id'], company_id=d['company_id'])
                .select_related('company'))
        print(f"  profile#{d['sales_profile_id']} company '{rows[0].company}' x{d['n']}"
              f"  -> membership ids {[r.pk for r in rows]}")

    # Blank codes: allowed by the constraint only once per company.
    blanks = (SalesStaffCompany.objects
              .filter(employee_code__in=['', None])
              .values('company_id')
              .annotate(n=Count('id'))
              .filter(n__gt=1))
    show(blanks, "More than one blank employee_code in the same company")
    for b in blanks:
        rows = SalesStaffCompany.objects.filter(
            company_id=b['company_id'], employee_code__in=['', None]).select_related('company')
        print(f"  company '{rows[0].company}' has {b['n']} rows with no employee code"
              f"  -> membership ids {[r.pk for r in rows]}")

    if not (dup_codes or dup_pairs or blanks):
        print("\nNo constraint conflicts found. If a save still fails, the duplicate is "
              "being introduced by the row you are editing.")
    return 0


if __name__ == '__main__':
    _sys.exit(main())

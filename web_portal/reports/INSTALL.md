# reports — Crystal Reports proxy

Adds `POST /api/reports/generate`. Authenticates the caller, checks per-user report access,
then proxies to the internal Crystal Reports service (a separate .NET app) and returns the
rendered PDF / Excel / Word file.

This app contains **only the Django side**. The Crystal service is a separate Windows
application that must be reachable over HTTP from this project.

Imported from `F:\samad\reporting_module` on 2026-08-25. Already wired up — this file records
what was done and what differs from the upstream INSTALL.md.

---

## Already wired

| Where | What |
|---|---|
| `web_portal/settings.py` | `'reports'` in `INSTALLED_APPS`; `CRYSTAL_SERVICE_*` settings; a `reports` logger |
| `web_portal/urls.py` | `path('api/reports/', include('reports.urls'))`; `/admin/reports/generate/` |
| `/admin/` | 4 model pages, plus a **Generate Report** run page (`reports/admin_views.py`) |
| `/swagger/` | `reports` tag -> `POST /reports/generate`, ported to drf-yasg |
| `.env` | `CRYSTAL_SERVICE_*` placeholders |
| database | `migrate reports` applied; 6 reports seeded |

## Three deliberate departures from the upstream INSTALL.md

Do not "fix" these back — each would break something else in the portal.

1. **No global `EXCEPTION_HANDLER`.** Upstream asks for
   `REST_FRAMEWORK["EXCEPTION_HANDLER"] = "reports.exceptions.reporting_exception_handler"`.
   This project already uses `monitoring.exceptions.logging_exception_handler` for every
   endpoint. The reports handler is scoped to its own view instead, via
   `GenerateReportView.get_exception_handler()`. Only `/api/reports/generate` returns the
   `{"error": ...}` shape; everything else is unchanged.

2. **No `URL_FORMAT_OVERRIDE = None`.** Upstream sets it to suppress a misleading format
   dropdown in its Swagger. This project relies on `?format=csv` / `?format=xlsx` for exports
   on every list endpoint (`web_portal/api_export.py`), and setting it to `None` would kill
   all of them.

3. **drf-yasg, not drf-spectacular.** The upstream `@extend_schema` block was ported to
   `@swagger_auto_schema`, so the endpoint appears in the project's existing `/swagger/`
   with no second docs page and no new dependencies. The `report_name` dropdown is built by
   `query_serializer=ReportSelectionQuerySerializer`, which is evaluated at schema-generation
   time — so a Report added in `/admin/` shows up without a redeploy, and nothing queries the
   database at import time (which would break `migrate` on a fresh install).

## Configure

Fill these in `.env` (project root, next to `manage.py`'s parent) and restart:

    CRYSTAL_SERVICE_BASE_URL=http://<crystal-host>:5000
    CRYSTAL_SERVICE_API_KEY=<must match the .NET service's ServiceAuth:ApiKey>
    CRYSTAL_SERVICE_API_KEY_HEADER=X-Internal-Api-Key
    CRYSTAL_SERVICE_TIMEOUT_SECONDS=30
    CRYSTAL_SERVICE_VERIFY_TLS=true

Leaving `CRYSTAL_SERVICE_BASE_URL` blank is safe: the portal boots normally and only
`/api/reports/generate` fails, with a 502 naming the missing setting.

## Grant access

Users see only reports granted to them. `<user>` is an **email address or username** — this
project authenticates by email.

    python manage.py grant_report_access <user> --all
    python manage.py grant_report_access <user> SalesRegister

Or from `/admin/reports/userreportaccess/`.

> Upstream's INSTALL.md documented a `--reports` flag that never existed, and `--all` was not
> implemented. Both now work as documented above.

## Smoke test

    curl -X POST http://localhost:8000/api/token/ \
      -H "Content-Type: application/json" \
      -d '{"email":"<user>","password":"<pass>"}'

    curl -X POST "http://localhost:8000/api/reports/generate?company=4B-BIO_LIVE&CustomerCardCode=BIC00038&FromDate=2023-01-01&ToDate=2026-08-22&report_name=CustomerDetailLedgerWithSummary" \
      -H "Authorization: Bearer <access-token>" \
      -H "Content-Type: application/json" -d '{}' -o out.pdf

## Errors you will actually hit

| Status | Meaning |
|---|---|
| 400 | Parameter not valid for that report (e.g. `CustomerCardCode` to ProductLedgerWithSummary) |
| 401 | Missing/expired JWT |
| 403 | No `UserReportAccess` row for this user + report |
| 404 | Unknown or inactive `report_name` |
| 502 | Crystal service unreachable/unconfigured, or the report failed to render |
| 504 | Crystal service timed out |

Report attempts are logged to `logs/app.log` (and failures to `logs/errors.log`) under the
`reports` logger, one line per call with user, report, parameters and elapsed ms.

## Open issues carried over from upstream testing

- Customer codes are **company-specific and exactly 8 characters**: `BIC…` in `4B-BIO_LIVE`,
  `AGC…` in `4B-AGRI_LIVE`, `ORC…` in `4B-ORANG_LIVE`. A code from the wrong company returns
  an empty report rather than an error.
- `ALLOWED_COMPANIES` in `reports/views.py` lists `4B-SEEDS_LIVE` and `4B-GROUP_LIVE`. Those
  two schemas do **not** exist on `fourb.vdc.services` (verified 2026-08-25: only
  `4B-AGRI_LIVE`, `4B-BIO_LIVE`, `4B-BIO_TEST`, `4B-ORANG_LIVE`, `BIO_TEST_LEDGER_OPTIMIZATION`,
  `FB_GEN`). Confirm against whatever instance the Crystal service points at, and trim the set.
- **Branch / sales-employee scoping does not restrict.** `apply_scope_filters` only rejects a
  request that *explicitly names* a branch outside the user's allowlist. A user with
  `BranchAccess` rows who simply omits `Branch` still gets an unrestricted report, and neither
  `Branch` nor `SalesEmployee` is query-overridable. Needs a decision before it is relied on
  as a security boundary.
- `CustomerDetailLedgerWithSummary` returns headers only unless a customer is supplied.
- `ProductLedgerWithSummary` has no customer prompt; filter it with `ItemCode` / `Warehouse`.
- `4bGeneralLedger` and `CollectionDetailReport` ignore the customer filter, and
  Region / Zone / Territory do not filter on any report. Both are report-side issues.
- Widening `SalesRegister` much past six months can fail with HANA error 305, caused by a
  single-row subquery inside that report's own SQL.
- `logging_utils.ReportingJsonFormatter` is unused here — the project has its own logging
  config. It uses `datetime.utcfromtimestamp`, deprecated on this stack's Python 3.13, so fix
  that before wiring it up.

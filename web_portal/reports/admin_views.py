"""Admin page for running a report and downloading the file.

The API at POST /api/reports/generate is the contract for the frontend; this is
the same thing for staff who just want the PDF now. It deliberately reuses the
API's service layer (apply_scope_filters -> resolve_crystal_parameters ->
CrystalReportServiceClient) rather than re-implementing it, so the two can't
drift, and it applies the same UserReportAccess check.
"""

import json
import logging
import time

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from rest_framework.exceptions import APIException

from . import registry, scoping
from .models import Report
from .permissions import CanAccessReport
from .serializers import ISO_DATE_PATTERN
from .services import CrystalReportServiceClient, apply_scope_filters, resolve_crystal_parameters
from .views import ALLOWED_COMPANIES, _FILE_EXTENSIONS, _QUERY_OVERRIDABLE_PARAMETERS

logger = logging.getLogger("reports")

FORMATS = tuple((value, label) for value, label in registry.EXPORT_FORMATS)


def _field_catalogue():
    """Every parameter box to render, plus which reports each one belongs to.

    The page shows one set of inputs and hides the ones the selected report does
    not own - the registry says a report 400s if sent a prompt it has no parameter
    for, so this is correctness, not just tidiness.
    """
    seen = {}
    for report in registry.iter_reports():
        for spec in report.parameters:
            entry = seen.setdefault(spec.name, {
                "name": spec.name,
                "label": spec.label,
                "type": "date" if spec.type == registry.DATE else "text",
                "placeholder": getattr(spec, "placeholder", "") or "",
                "hint": (spec.help_text or "").strip(),
                "danger": bool(getattr(spec, "danger", False)),
                "reports": [],
                "required_for": [],
            })
            entry["reports"].append(report.key)
            if spec.required:
                entry["required_for"].append(report.key)
    return [seen[name] for name in registry.QUERY_PARAMETERS if name in seen]


def _report_meta():
    """Per-report notes and defaults, for the JS that reacts to the picker."""
    return {
        report.key: {
            "notes": (report.notes or "").strip(),
            "params": [spec.name for spec in report.parameters],
            "required": [spec.name for spec in report.parameters if spec.required],
            "defaultCompany": report.default_company or "",
            "maxSpanDays": getattr(report, "max_span_days", None),
        }
        for report in registry.iter_reports()
    }


def _accessible_reports(user):
    """Reports this user may run - the same rule the API enforces.

    Note this is UserReportAccess, not is_superuser: a superuser with no grant
    rows sees an empty list here exactly as they would get a 403 from the API.
    """
    return Report.objects.filter(is_active=True, user_access__user=user).order_by("display_name")


def _admin_context(request):
    """The custom admin site's own context (nav sidebar, app list, branding)."""
    try:
        from web_portal.admin import admin_site
    except ImportError:  # pragma: no cover - standalone install
        from django.contrib import admin as _admin
        admin_site = _admin.site
    return admin_site.each_context(request)


def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _fail(request, context, message):
    """One error path for both submit styles.

    The page posts through fetch() so it can show a progress overlay, and a
    fetch caller wants JSON, not a whole re-rendered page. A plain form POST
    (JS off, or an older cached page) still gets the HTML.
    """
    if _is_ajax(request):
        return JsonResponse({"error": message}, status=400)
    context["error"] = message
    return render(request, "admin/reports/generate.html", context)


PERMISSION = "reports.generate_report"

# Fields whose values are chosen from a SAP-backed, user-scoped list rather
# than typed. The server re-derives the scope on submit, so a hand-edited
# value cannot widen it.
LOOKUP_FIELDS = {
    "CustomerCardCode": "customers",
    "Region": "region",
    "Zone": "zone",
    "Territory": "territory",
}


def report_lov_admin(request):
    """Options for the page's searchable pickers, scoped to the caller.

    The employee code is taken from request.user here and nowhere else - it is
    never accepted from the querystring, or a sales user could read another
    employee's dealers by editing the URL.
    """
    if not request.user.has_perm(PERMISSION):
        raise PermissionDenied

    kind = (request.GET.get("kind") or "").strip().lower()
    company = (request.GET.get("company") or "").strip()
    search = (request.GET.get("q") or "").strip()

    allowed = scoping.allowed_companies(request.user, ALLOWED_COMPANIES)
    if company and company not in allowed:
        return JsonResponse(
            {"results": [], "error": "You do not have access to that company."}, status=403
        )
    if not company:
        if len(allowed) != 1:
            return JsonResponse({"results": [], "error": "Choose a company first."})
        company = allowed[0]

    if kind == "customers":
        rows, error = scoping.customers_for(request.user, company, search=search, limit=50)
    elif kind in ("region", "zone", "territory"):
        rows, error = scoping.geo_for(request.user, company, kind, search=search)
    else:
        return JsonResponse({"results": [], "error": f"Unknown list '{kind}'."}, status=400)

    return JsonResponse({"results": rows, "error": error})


def generate_report_admin(request):
    if not request.user.has_perm(PERMISSION):
        raise PermissionDenied
    reports = list(_accessible_reports(request.user))
    submitted = {key: (request.POST.get(key) or "").strip() for key in
                 ("report_name", "company", "format") + _QUERY_OVERRIDABLE_PARAMETERS}
    # Built here rather than in the template: Django templates can't look a key
    # up in a dict by a loop variable, so everything a box needs travels with it.
    fields = [
        dict(entry, value=submitted[entry["name"]], lookup=LOOKUP_FIELDS.get(entry["name"], ""))
        for entry in _field_catalogue()
    ]
    # each_context() carries is_nav_sidebar_enabled and available_apps; without
    # it the admin renders this page with no left navigation at all.
    context = {
        **_admin_context(request),
        "title": "Generate Report",
        "reports": reports,
        "companies": scoping.allowed_companies(request.user, ALLOWED_COMPANIES),
        "company_locked": len(scoping.allowed_companies(request.user, ALLOWED_COMPANIES)) == 1,
        "lookup_fields_json": json.dumps(LOOKUP_FIELDS),
        "formats": FORMATS,
        "fields": fields,
        "report_meta_json": json.dumps(_report_meta()),
        "submitted": submitted,
        "error": None,
    }

    if request.method != "POST":
        return render(request, "admin/reports/generate.html", context)

    report_name = submitted["report_name"]
    export_format = submitted["format"] or "pdf"
    company = submitted["company"]

    report = Report.objects.filter(name=report_name, is_active=True).first()
    if report is None:
        return _fail(request, context, "Pick a report to run.")
    if not CanAccessReport().has_object_permission(request, None, report):
        return _fail(request, context, (
            f"You do not have access to '{report.display_name}'. "
            "Ask an administrator for a User report access row."
        ))
    permitted = scoping.allowed_companies(request.user, ALLOWED_COMPANIES)
    if not company and len(permitted) == 1:
        company = permitted[0]           # locked field posts nothing; apply it here
    if company and company not in permitted:
        return _fail(request, context,
                     "You do not have access to that company. Pick one of your own.")

    # Only send prompts this report actually owns. Boxes for other reports are
    # hidden by CSS, but hidden inputs still post, and the service answers 400
    # for a prompt the .rpt has no parameter for.
    spec = registry.get_report(report_name)
    owned = {p.name for p in spec.parameters} if spec else set(_QUERY_OVERRIDABLE_PARAMETERS)

    parameters = {}
    for name in _QUERY_OVERRIDABLE_PARAMETERS:
        value = submitted[name] if name in owned else ""
        if not value:
            # An untouched box must stay absent: an empty string is a real filter
            # value to Crystal ("CardCode = ''") and matches nothing.
            continue
        if name.endswith("Date") and not ISO_DATE_PATTERN.match(value):
            return _fail(request, context,
                         f"'{name}' must be in YYYY-MM-DD format, got '{value}'.")
        parameters[name] = value

    log_context = {
        "user_id": request.user.id,
        "report_name": report_name,
        "report_format": export_format,
        "company": company or "as authored",
        "parameters": parameters,
        "source": "admin",
    }
    started_at = time.monotonic()

    try:
        scoped = apply_scope_filters(request.user, parameters)
        crystal_parameters = resolve_crystal_parameters(report_name, scoped)
        content, content_type = CrystalReportServiceClient().generate(
            report_name, export_format, crystal_parameters, company or None
        )
    except APIException as exc:
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.warning(
            "Report generation failed", extra={**log_context, "success": False, "elapsed_ms": elapsed_ms}
        )
        return _fail(request, context, str(exc.detail if hasattr(exc, "detail") else exc))
    except Exception as exc:  # noqa: BLE001 - the page must not 500 on a bad report
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.exception(
            "Report generation failed", extra={**log_context, "success": False, "elapsed_ms": elapsed_ms}
        )
        return _fail(request, context,
                     "Something went wrong while generating this report. The details "
                     "have been logged - please tell IT if it keeps happening.")

    elapsed_ms = int((time.monotonic() - started_at) * 1000)
    logger.info(
        "Report generated successfully", extra={**log_context, "success": True, "elapsed_ms": elapsed_ms}
    )

    filename = f"{report_name}.{_FILE_EXTENSIONS.get(export_format, 'bin')}"
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

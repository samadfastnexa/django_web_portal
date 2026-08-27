import logging
import time

from django.http import HttpResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from .exceptions import (
    ReportNotFoundError,
    ReportPermissionDenied,
    ReportValidationError,
    reporting_exception_handler,
)
from .models import Report
from .permissions import CanAccessReport
from .renderers import BinaryFileRenderer
from .serializers import (
    ISO_DATE_PATTERN,
    ReportGenerationRequestSerializer,
    ReportSelectionQuerySerializer,
)
from .registry import ALLOWED_COMPANIES, FILE_EXTENSIONS, QUERY_PARAMETERS
from .services import CrystalReportServiceClient, apply_scope_filters, resolve_crystal_parameters

logger = logging.getLogger("reports")

# Catalogue values come from registry.py, the file shipped by the reporting
# project, so the allowed companies / extensions / parameter names cannot drift
# from what the .NET service actually accepts.
_FILE_EXTENSIONS = FILE_EXTENSIONS
_QUERY_OVERRIDABLE_PARAMETERS = QUERY_PARAMETERS


_DESCRIPTION = """Checks the caller's UserReportAccess and branch/sales-employee scoping, then proxies to the
internal Crystal Reports service and streams back the rendered file (PDF/Excel/Word) as an
attachment.

## Example values

**company** - which SAP Business One company to read. Omit to use the company the report was
authored against.

| company | customer codes look like |
|---|---|
| `4B-BIO_LIVE` | `BIC00038`, `BIC00425`, `BIC00543`, `BIC00536` |
| `4B-AGRI_LIVE` | `AGC00980`, `AGC00790`, `AGC00891`, `AGC00589` |
| `4B-ORANG_LIVE` | `ORC00037`, `ORC00264`, `ORC00154`, `ORC00276` |

**CustomerCardCode** must belong to the company you asked for. A BIO code against AGRI returns
an empty report - the code simply does not exist there. Codes are always 8 characters; a
truncated code such as `AGC0098` matches nothing.

**FromDate / ToDate** - `YYYY-MM-DD`. Data spans roughly 2023-01-01 to 2026-08-22, except
CUSDETAIL12 (CustomerDetailLedgerWithSummary), which starts 2024-09.

**Region / Zone / Territory** - real values from CWL, per company. Most reports prompt for the
numeric id; CollectionDetailReport prompts for the name instead, and sending the wrong kind
returns a Crystal type error naming the parameter.

| company | Region (id = name) | Zone (id = name) | Territory (id = name) |
|---|---|---|---|
| `4B-BIO_LIVE` | `1` = Blue Region, `298` = Baluchistan Region | `262` = Bahawalpur Zone, `306` = Bahawalnagar Zone | `28` = Ali Pur Territory, `244` = Arifwala Territory |
| `4B-AGRI_LIVE` | `136` = AGRI GREEN, `237` = AGRI WHITE, `427` = AGRI BLUE | `102` = BAHAWALNAGAR Zone, `201` = ARIF WALA Zone, `25` = BHAKHAR Zone | `90` = Ahmad Pur East Territory, `413` = 18 HAZARI Territory |
| `4B-ORANG_LIVE` | `198` = Atlantic Rhinos Region, `212` = E-commerce Region | `62` = Ali Pur Zone, `29` = Arif Wala Zone | `64` = Ali Pur Territory, `31` = Arif Wala Territory |

Known limitation: supplying Region, Zone or Territory currently returns an empty report on every
report tested, with a correct id as well as an impossible one, so the filter is not usable yet.
The cause is in the reports themselves rather than this API.

## Which parameters each report takes

| report_name | company | customer filter | verified example |
|---|---|---|---|
| `SalesRegister` | any | works | `BIC00425` / `AGC00589` / `ORC00154`, 6-month range |
| `CustomerDetailLedgerWithSummary` | any | **required** - headers only without it | `BIC00038` / `AGC00980` / `ORC00037` |
| `BusinessHistory` | any | works, but one customer is a short summary | `AGC00980` |
| `4bGeneralLedger` | AGRI | ignored - run unfiltered | dates only |
| `CollectionDetailReport` | AGRI | ignored - run unfiltered | dates only |
| `ProductLedgerWithSummary` | **BIO only** | no customer prompt; filters on ItemCode/Warehouse instead | `ItemCode=FG00563`, 2023-01-01..2026-08-22 |

Sending `CustomerCardCode` to `ProductLedgerWithSummary` returns 400. Note that Swagger keeps
the last example body you selected, so clear the body to `{}` when driving the call purely from
query parameters.

## Errors

| Status | Meaning |
|---|---|
| 400 | Parameter not valid for that report |
| 401 | Missing/expired JWT |
| 403 | No UserReportAccess row for this user + report |
| 404 | Unknown or inactive report_name |
| 502 | Crystal service unreachable, or the report failed to render |
| 504 | Crystal service timed out |
"""

_ERROR_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
)


class GenerateReportView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer, BinaryFileRenderer]

    def get_exception_handler(self):
        """Scope the module's {"error": ...} handler to this view.

        The project-wide EXCEPTION_HANDLER (monitoring.exceptions) stays in place
        for every other endpoint - this module must not change how the rest of the
        API reports errors.
        """
        return reporting_exception_handler

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        # A client asking for application/octet-stream (Swagger's default here, since the
        # success response is a file) would otherwise get error bodies labelled as binary
        # too - which browsers offer as a mystery download instead of showing the message.
        # Errors are always JSON, so label them as such.
        if response.status_code >= 400 and isinstance(response.accepted_renderer, BinaryFileRenderer):
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = JSONRenderer.media_type
        return response

    @swagger_auto_schema(
        tags=["reports"],
        operation_id="reports_generate",
        operation_summary="Generate a report",
        operation_description=_DESCRIPTION,
        request_body=ReportGenerationRequestSerializer,
        query_serializer=ReportSelectionQuerySerializer,
        manual_parameters=[
            openapi.Parameter(
                "company", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                enum=sorted(ALLOWED_COMPANIES),
                description=(
                    "SAP Business One company to read. Leave blank to use the company the "
                    "report was authored against (SalesRegister and ProductLedgerWithSummary "
                    "read BIO, the others AGRI). Customer codes are company-specific, so this "
                    "must match the code you pass."
                ),
            ),
            openapi.Parameter(
                "FromDate", openapi.IN_QUERY, type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
                required=False,
                description=(
                    "Start date, YYYY-MM-DD. Applies to every report. Data runs roughly "
                    "2023-01-01 to 2026-08-22; CustomerDetailLedgerWithSummary reads CUSDETAIL12 "
                    "which only starts 2024-09, so earlier ranges are legitimately empty."
                ),
            ),
            openapi.Parameter(
                "ToDate", openapi.IN_QUERY, type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE,
                required=False,
                description=(
                    "End date, YYYY-MM-DD. Applies to every report. On SalesRegister keep the "
                    "span near six months - wider ranges can fail with HANA error 305, a "
                    "single-row subquery in that report's own SQL returning more than one row."
                ),
            ),
            openapi.Parameter(
                "CustomerCardCode", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "Business Partner CardCode. Always 8 characters - a truncated code such as "
                    "AGC0098 matches nothing. The prefix must match `company`: "
                    "BIO -> BIC00038, BIC00425, BIC00543; "
                    "AGRI -> AGC00980, AGC00790, AGC00891; "
                    "ORANG -> ORC00037, ORC00264, ORC00154. "
                    "Not accepted by ProductLedgerWithSummary, which has no customer prompt."
                ),
            ),
            openapi.Parameter(
                "Region", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "NOT YET WORKING - returns an empty report for a valid id as well as an "
                    "impossible one; the fault is in the reports, not this API. "
                    "Numeric RegionId on most reports, RegionName text on "
                    "CollectionDetailReport. BIO 1=Blue Region, 298=Baluchistan Region; "
                    "AGRI 136=AGRI GREEN, 237=AGRI WHITE, 427=AGRI BLUE; "
                    "ORANG 198=Atlantic Rhinos Region, 212=E-commerce Region."
                ),
            ),
            openapi.Parameter(
                "Zone", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "NOT YET WORKING - see Region. Numeric ZoneId on most reports, ZoneName "
                    "text on CollectionDetailReport. BIO 262=Bahawalpur Zone, "
                    "306=Bahawalnagar Zone; AGRI 102=BAHAWALNAGAR Zone, 201=ARIF WALA Zone; "
                    "ORANG 62=Ali Pur Zone, 29=Arif Wala Zone."
                ),
            ),
            openapi.Parameter(
                "Territory", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "NOT YET WORKING - see Region. Numeric TerritoryId on most reports, "
                    "TerritoryName text on CollectionDetailReport. BIO 28=Ali Pur Territory, "
                    "244=Arifwala Territory; AGRI 90=Ahmad Pur East Territory, "
                    "413=18 HAZARI Territory; ORANG 64=Ali Pur Territory, "
                    "31=Arif Wala Territory."
                ),
            ),
            openapi.Parameter(
                "ItemCode", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "ProductLedgerWithSummary only, and the filter works. BIO example with "
                    "data: FG00563. The report returns a summary when unfiltered and detail "
                    "when an item is given, so a filtered run is usually larger. An item with "
                    "no ledger rows in the range returns headers only."
                ),
            ),
            openapi.Parameter(
                "Project", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "BusinessHistory only. SAP project code; leave blank for all projects."
                ),
            ),
            openapi.Parameter(
                "BatchNo", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "ProductLedgerWithSummary only. SAP batch number; blank for all batches."
                ),
            ),
            openapi.Parameter(
                "Warehouse", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False,
                description=(
                    "ProductLedgerWithSummary only. LEAVE BLANK - any warehouse other "
                    "than the report's saved default (WH09) fails with HANA error 257, "
                    "because this prompt is substituted straight into the report SQL. "
                    "Use ItemCode to narrow instead; that one filters correctly."
                ),
            ),
        ],
        responses={
            200: openapi.Response(
                description="The rendered report file, as an attachment.",
                schema=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_BINARY),
            ),
            400: openapi.Response("Parameter not valid for that report.", _ERROR_SCHEMA),
            401: openapi.Response("Missing or expired JWT.", _ERROR_SCHEMA),
            403: openapi.Response("No access to this report.", _ERROR_SCHEMA),
            404: openapi.Response("Unknown or inactive report_name.", _ERROR_SCHEMA),
            502: openapi.Response("Crystal service unreachable or render failed.", _ERROR_SCHEMA),
            504: openapi.Response("Crystal service timed out.", _ERROR_SCHEMA),
        },
    )
    def post(self, request):
        payload = dict(request.data)
        # Swagger can only offer report_name as a dropdown by making it a query
        # parameter, so accept it from either place with the query taking priority.
        if request.query_params.get("report_name"):
            payload["report_name"] = request.query_params["report_name"]

        serializer = ReportGenerationRequestSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report_name = data["report_name"]
        export_format = data["format"]
        company = (request.query_params.get("company") or data.get("company") or "").strip()
        if company and company not in ALLOWED_COMPANIES:
            raise ReportValidationError(
                f"Unknown company '{company}'. Allowed: {', '.join(sorted(ALLOWED_COMPANIES))}."
            )
        parameters = dict(data.get("parameters", {}))

        for name in _QUERY_OVERRIDABLE_PARAMETERS:
            value = request.query_params.get(name)
            if value:
                if name.endswith("Date") and not ISO_DATE_PATTERN.match(value):
                    raise ReportValidationError(f"'{name}' must be in YYYY-MM-DD format, got '{value}'.")
                parameters[name] = value

        # Swagger submits every field it renders, so an untouched optional box arrives
        # as "". Passing that through sets the Crystal parameter to an empty string,
        # which is a real filter value ("CardCode = ''") and matches nothing - drop it
        # instead so the parameter keeps its default, same as omitting it entirely.
        parameters = {k: v for k, v in parameters.items() if v != "" and v is not None}

        report = Report.objects.filter(name=report_name, is_active=True).first()
        if report is None:
            raise ReportNotFoundError(f"Report '{report_name}' was not found.")

        if not CanAccessReport().has_object_permission(request, self, report):
            raise ReportPermissionDenied()

        scoped_parameters = apply_scope_filters(request.user, parameters)
        crystal_parameters = resolve_crystal_parameters(report_name, scoped_parameters)

        log_context = {
            "user_id": request.user.id,
            "report_name": report_name,
            "report_format": export_format,
            "company": company or "as authored",
            "parameters": scoped_parameters,
        }
        started_at = time.monotonic()

        try:
            content, content_type = CrystalReportServiceClient().generate(
                report_name, export_format, crystal_parameters, company or None
            )
        except Exception:
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            logger.exception(
                "Report generation failed", extra={**log_context, "success": False, "elapsed_ms": elapsed_ms}
            )
            raise

        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.info(
            "Report generated successfully", extra={**log_context, "success": True, "elapsed_ms": elapsed_ms}
        )

        filename = f"{report_name}.{_FILE_EXTENSIONS.get(export_format, 'bin')}"
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

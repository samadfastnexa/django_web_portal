import requests
from django.conf import settings

from .exceptions import (
    CrystalServiceError,
    CrystalServiceTimeout,
    ReportNotFoundError,
    ReportPermissionDenied,
    ReportValidationError,
)
from .models import BranchAccess, SalesEmployeeAccess

# Parameter aliases, report catalogue and format names all live in registry.py,
# which is the file shipped by the reporting project. Re-exported here so the
# rest of the app keeps its existing import points and the two can never drift.
from .registry import (  # noqa: F401
    DOTNET_FORMAT_NAMES as _DOTNET_FORMAT_NAMES,
    CRYSTAL_PARAMETER_ALIASES as _CRYSTAL_PARAMETER_ALIASES,
    resolve_crystal_parameters,
)


def apply_scope_filters(user, parameters):
    """Enforces the caller's Branch/SalesEmployee restrictions against the
    requested parameters. A dimension with no access rows for the user is
    treated as unrestricted for that dimension.
    """
    scoped = dict(parameters)

    branch_ids = set(BranchAccess.objects.filter(user=user).values_list("branch_id", flat=True))
    if branch_ids:
        requested_branch = scoped.get("Branch")
        if requested_branch is not None and str(requested_branch) not in branch_ids:
            raise ReportPermissionDenied(f"You do not have access to branch '{requested_branch}'.")

    sales_employee_ids = set(
        SalesEmployeeAccess.objects.filter(user=user).values_list("sales_employee_id", flat=True)
    )
    if sales_employee_ids:
        requested_employee = scoped.get("SalesEmployee")
        if requested_employee is not None and str(requested_employee) not in sales_employee_ids:
            raise ReportPermissionDenied(f"You do not have access to sales employee '{requested_employee}'.")

    return scoped


class CrystalReportServiceClient:
    """Thin HTTP client for the ASP.NET Core Crystal Reports service."""

    def __init__(self):
        # Read lazily rather than at import: an unconfigured install should fail
        # on the one endpoint that needs it, not stop the whole portal booting.
        base_url = (getattr(settings, "CRYSTAL_SERVICE_BASE_URL", "") or "").strip()
        if not base_url:
            raise CrystalServiceError(
                "CRYSTAL_SERVICE_BASE_URL is not configured - set it in .env "
                "(see reports/INSTALL.md) and restart."
            )
        self.base_url = base_url.rstrip("/")
        self.api_key_header = getattr(settings, "CRYSTAL_SERVICE_API_KEY_HEADER", "X-Internal-Api-Key")
        self.api_key = getattr(settings, "CRYSTAL_SERVICE_API_KEY", "")
        self.timeout = (
            float(getattr(settings, "CRYSTAL_SERVICE_CONNECT_TIMEOUT_SECONDS", 10.0)),
            float(getattr(settings, "CRYSTAL_SERVICE_TIMEOUT_SECONDS", 120.0)),
        )
        self.verify_tls = getattr(settings, "CRYSTAL_SERVICE_VERIFY_TLS", True)

    def generate(self, report_name, export_format, parameters, company=None):
        payload = {
            "reportName": report_name,
            "format": _DOTNET_FORMAT_NAMES.get(export_format, "Pdf"),
            "parameters": {key: str(value) for key, value in parameters.items()},
        }
        if company:
            payload["company"] = company
        headers = {self.api_key_header: self.api_key}

        try:
            response = requests.post(
                f"{self.base_url}/api/reports/generate",
                json=payload,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_tls,
            )
        except requests.Timeout as exc:
            raise CrystalServiceTimeout() from exc
        except requests.RequestException as exc:
            raise CrystalServiceError(f"Could not reach the reporting service: {exc}") from exc

        if response.status_code == 404:
            raise ReportNotFoundError(self._error_message(response, "Report not found."))
        if response.status_code == 400:
            raise ReportValidationError(self._error_message(response, "Invalid report parameters."))
        if response.status_code == 401:
            raise CrystalServiceError("Rejected by the reporting service (invalid internal API key).")
        if not response.ok:
            raise CrystalServiceError(
                self._error_message(response, "The reporting service failed to generate the report.")
            )

        content_type = response.headers.get("Content-Type", "application/octet-stream")
        return response.content, content_type

    @staticmethod
    def _error_message(response, default):
        try:
            return response.json().get("error", default)
        except ValueError:
            return default

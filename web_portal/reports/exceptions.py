import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("reports")


class ReportNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Report not found."
    default_code = "report_not_found"


class ReportPermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have access to this report."
    default_code = "report_permission_denied"


class ReportValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid report parameters."
    default_code = "report_validation_error"


class CrystalServiceError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "The reporting service failed to generate the report."
    default_code = "crystal_service_error"


class CrystalServiceTimeout(APIException):
    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_detail = "Timed out waiting for the reporting service."
    default_code = "crystal_service_timeout"


def reporting_exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER: normalizes error responses to {"error": ...} and logs them."""
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    user = getattr(request, "user", None)
    user_id = getattr(user, "id", None)

    if response is not None:
        logger.warning(
            "Report API error: %s",
            exc,
            extra={"user_id": user_id, "status_code": response.status_code},
        )
        if isinstance(response.data, dict) and "detail" in response.data:
            response.data = {"error": response.data["detail"]}
        elif not isinstance(response.data, dict):
            response.data = {"error": response.data}
        return response

    logger.exception("Unhandled exception in reports API", extra={"user_id": user_id})
    return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

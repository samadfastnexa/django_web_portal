import re

from rest_framework import serializers

from .models import Report

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def active_report_choices():
    """Report names available to run, as (value, label) pairs.

    Read per-call rather than cached at import so the dropdown reflects
    whatever is active in the DB right now - adding a Report in /admin/
    surfaces it without a redeploy.
    """
    return [
        (name, display_name or name)
        for name, display_name in Report.objects.filter(is_active=True)
        .order_by("display_name")
        .values_list("name", "display_name")
    ]


class ReportParametersSerializer(serializers.Serializer):
    """Named, documented parameters for known reports - shows up as individual
    fields in Swagger instead of one freeform JSON object.

    Any key not declared here still passes through unvalidated (see
    to_internal_value below), so reports without named fields yet - or a
    raw Crystal parameter name - keep working exactly as before. Add a
    field here per report as its parameters get wired up in
    reports.services._CRYSTAL_PARAMETER_ALIASES.
    """

    FromDate = serializers.DateField(
        required=False, help_text="SalesRegister: report start date."
    )
    ToDate = serializers.DateField(
        required=False, help_text="SalesRegister: report end date."
    )
    CustomerCardCode = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="SalesRegister: SAP B1 Business Partner CardCode to filter by.",
    )

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        for key, value in data.items():
            if key not in self.fields:
                validated[key] = value
        return validated


class ReportGenerationRequestSerializer(serializers.Serializer):
    report_name = serializers.ChoiceField(choices=[])
    format = serializers.ChoiceField(choices=["pdf", "excel", "word"], default="pdf")
    parameters = ReportParametersSerializer(required=False, default=dict)
    # Optional SAP Business One company schema, e.g. "4B-AGRI_LIVE". Omitted means "whatever
    # the .rpt was authored against", so existing callers keep their current behaviour.
    company = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["report_name"].choices = active_report_choices()

    def validate_parameters(self, parameters):
        # FromDate/ToDate are already DateFields; this catches any other
        # *Date key that arrives through ReportParametersSerializer's
        # passthrough for undeclared parameters.
        for key, value in parameters.items():
            if key.endswith("Date") and not ISO_DATE_PATTERN.match(str(value)):
                raise serializers.ValidationError(
                    f"'{key}' must be in YYYY-MM-DD format, got '{value}'."
                )
        return parameters


class ReportSelectionQuerySerializer(serializers.Serializer):
    """Exploded into query parameters by drf-yasg's `query_serializer` so Swagger
    renders report_name as a real dropdown. Swagger only builds interactive widgets
    for query/path parameters - a field declared solely in the JSON request body
    shows up as raw text no matter how it's typed.

    It must stay a serializer rather than a hardcoded openapi.Parameter: this is
    instantiated when the schema is generated (per request, cache_timeout=0), so
    a Report added in /admin/ appears in the dropdown without a redeploy - and
    nothing touches the database at import time, which would break `migrate` on a
    fresh install.
    """

    report_name = serializers.ChoiceField(
        choices=[],
        required=False,
        help_text="Report to run. Overrides report_name in the body.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["report_name"].choices = active_report_choices()

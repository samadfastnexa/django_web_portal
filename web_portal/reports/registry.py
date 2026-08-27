"""Static registry of the Crystal reports exposed through the Django admin.

There are no database models here and no migrations to run.  The six reports are
described by plain data, so the app needs nothing beyond ``INSTALLED_APPS``, a URL
include and a few settings.

The reason for a static registry rather than a lookup: the .NET ReportingService
has exactly one action, ``POST /api/reports/generate``.  It exposes no catalogue,
list or health endpoint, so there is nothing to discover reports from at runtime.
This file *is* the catalogue.

The module deliberately imports neither Django nor ``requests`` - it is pure data
plus a few functions, so it can be imported (and unit-tested) without settings
being configured.  The form layer lives in ``forms.py``, the HTTP client in
``services.py``.

Nothing in this module touches the internal API key or any HANA credential.
"""

import datetime
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Mapping, Optional, Tuple

__all__ = [
    "DATE",
    "TEXT",
    "INTEGER",
    "FIELD_TYPES",
    "FROM_DATE",
    "TO_DATE",
    "EXPORT_FORMATS",
    "EXPORT_FORMAT_VALUES",
    "DEFAULT_EXPORT_FORMAT",
    "DOTNET_FORMAT_NAMES",
    "FILE_EXTENSIONS",
    "CONTENT_TYPES",
    "COMPANY_CHOICES",
    "ALLOWED_COMPANIES",
    "Parameter",
    "Report",
    "REPORTS",
    "QUERY_PARAMETERS",
    "REPORT_CHOICES",
    "CRYSTAL_PARAMETER_ALIASES",
    "get_report",
    "iter_reports",
    "dotnet_format",
    "content_type_for",
    "filename_for",
    "is_blank",
    "serialize_value",
    "serialize_parameters",
    "resolve_crystal_parameters",
]


# ---------------------------------------------------------------------------
# Field kinds understood by the form builder
# ---------------------------------------------------------------------------

DATE = "date"        # -> forms.DateField rendered as <input type="date">, sent as YYYY-MM-DD
TEXT = "text"        # -> forms.CharField, sent stripped
INTEGER = "integer"  # -> forms.IntegerField, sent as str(value)

FIELD_TYPES = frozenset({DATE, TEXT, INTEGER})

# The two parameters every report shares.  Named here so the form layer can apply
# the from <= to check without hard-coding strings of its own.
FROM_DATE = "FromDate"
TO_DATE = "ToDate"


# ---------------------------------------------------------------------------
# Export formats
# ---------------------------------------------------------------------------

# Only PDF is exercised by the deployed reports.  The Excel and Word paths exist
# in the .NET exporter but have never been verified end to end, hence the labels.
EXPORT_FORMATS = (
    ("pdf", "PDF"),
    ("excel", "Excel (.xlsx) - not verified"),
    ("word", "Word (.doc) - not verified"),
)
EXPORT_FORMAT_VALUES = tuple(value for value, _label in EXPORT_FORMATS)
DEFAULT_EXPORT_FORMAT = "pdf"

# Wire values for the service's ``ReportExportFormat`` enum.  Case matters less
# than it looks (the enum is parsed case-insensitively) but send the canonical
# spelling anyway.
DOTNET_FORMAT_NAMES = {"pdf": "Pdf", "excel": "Excel", "word": "Word"}

# Extension used for the download.  Do NOT derive this from the response's
# Content-Type: the service labels the body from the format that was *requested*
# rather than from what Crystal actually produced.  Word in particular is exported
# as legacy .doc bytes under a .docx MIME type, so it is named .doc here on purpose.
FILE_EXTENSIONS = {"pdf": "pdf", "excel": "xlsx", "word": "doc"}

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "word": "application/msword",
}


# ---------------------------------------------------------------------------
# Companies (SAP schemas)
# ---------------------------------------------------------------------------

# Blank means "whatever company the .rpt was authored against": the renderer skips
# the schema override entirely when the field is empty.
#
# The allow-list is enforced on this side on purpose.  The service account can see
# every schema on the HANA instance, and an unknown schema is not rejected by the
# service - it reaches the database and comes back as an opaque connection failure.
COMPANY_CHOICES = (
    ("", "Default (as the report was authored)"),
    ("4B-BIO_LIVE", "4B Bio"),
    ("4B-AGRI_LIVE", "4B Agri"),
    ("4B-ORANG_LIVE", "4B Orange"),
    ("4B-SEEDS_LIVE", "4B Seeds"),
    ("4B-GROUP_LIVE", "4B Group"),
)
ALLOWED_COMPANIES = frozenset(value for value, _label in COMPANY_CHOICES if value)


# ---------------------------------------------------------------------------
# Registry data types
# ---------------------------------------------------------------------------


class _MappingCompat(object):
    """Read-only ``spec["key"]`` / ``spec.get("key")`` access.

    Attribute access (``spec.name``) is the intended API.  These mapping methods
    exist so that code written against a plain dict-shaped spec keeps working.
    """

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)


@dataclass(frozen=True)
class Parameter(_MappingCompat):
    """One report prompt, as the admin form should present it.

    ``name`` is the *friendly* name.  It is what the form field is called and what
    gets logged; the byte-exact Crystal prompt name it maps to is applied only at
    the last moment, by :func:`resolve_crystal_parameters`.
    """

    name: str
    label: str
    type: str = TEXT
    required: bool = False
    help_text: str = ""
    placeholder: str = ""
    max_length: Optional[int] = None
    min_value: Optional[int] = None
    #: Render inside a collapsed "Advanced filters" section.
    advanced: bool = False
    #: Render with a warning treatment - filling this in is known to break renders.
    danger: bool = False


@dataclass(frozen=True)
class Report(_MappingCompat):
    key: str
    label: str
    description: str
    parameters: Tuple[Parameter, ...]
    #: Company the .rpt itself points at, for reference in help text.
    authored_company: str = ""
    #: Pre-selected value of the company field; "" means "as authored".
    default_company: str = ""
    #: Offer the company selector at all.  The renderer accepts the override on
    #: every report, so this is True throughout; the flag exists so that a future
    #: report which must not be re-pointed can opt out without a code change.
    supports_company: bool = True
    formats: Tuple[str, ...] = EXPORT_FORMAT_VALUES
    default_format: str = DEFAULT_EXPORT_FORMAT
    #: Operator guidance shown above the form.
    notes: str = ""
    #: Soft (non-blocking) warning threshold for ToDate - FromDate, in days.
    max_span_days: Optional[int] = None

    @property
    def parameter_names(self) -> Tuple[str, ...]:
        return tuple(p.name for p in self.parameters)

    def parameter(self, name: str) -> Parameter:
        for spec in self.parameters:
            if spec.name == name:
                return spec
        raise KeyError(name)

    @property
    def basic_parameters(self) -> Tuple[Parameter, ...]:
        return tuple(p for p in self.parameters if not p.advanced)

    @property
    def advanced_parameters(self) -> Tuple[Parameter, ...]:
        return tuple(p for p in self.parameters if p.advanced)

    @property
    def format_choices(self) -> Tuple[Tuple[str, str], ...]:
        labels = dict(EXPORT_FORMATS)
        return tuple((value, labels[value]) for value in self.formats)


# ---------------------------------------------------------------------------
# Shared help text
# ---------------------------------------------------------------------------

_GEO_BROKEN = (
    " Not working yet: filtering by Region, Zone or Territory currently returns an "
    "empty report even for a valid value - the fault is in the report files "
    "themselves. Leave this blank."
)

_WAREHOUSE_WARNING = (
    "Leave this blank. The only warehouse this report can render is its own "
    "built-in default (WH09); any other warehouse code makes the whole report fail "
    "with a database error rather than simply filtering. Do not fill this in "
    "unless you have been told otherwise."
)

_CUSTOMER_CODE_NOTE = (
    "Codes are company-specific and 8 characters long - a shortened code such as "
    "AGC0098 matches nothing, and a Bio code run against Agri renders an empty "
    "report rather than an error."
)


def _from_date(help_text: str) -> Parameter:
    return Parameter(
        name=FROM_DATE, label="From date", type=DATE, required=True, help_text=help_text
    )


def _to_date(help_text: str) -> Parameter:
    return Parameter(
        name=TO_DATE, label="To date", type=DATE, required=True, help_text=help_text
    )


# ---------------------------------------------------------------------------
# The six reports
# ---------------------------------------------------------------------------

_REPORTS = (
    Report(
        key="SalesRegister",
        label="Sales Register",
        description="Sales invoices and returns for one customer over a date range.",
        authored_company="4B-BIO_LIVE",
        default_company="",
        max_span_days=200,
        notes=(
            "This is the only report with no 'all customers' option - without a "
            "customer code it renders an empty PDF. Keep the date range to about "
            "six months: wider ranges can fail inside the report's own SQL."
        ),
        parameters=(
            _from_date(
                "Start of the sales period. Data is available from about 2023-01-01."
            ),
            _to_date(
                "End of the sales period. Keep the range to roughly six months - "
                "wider ranges can fail inside the report's own SQL."
            ),
            Parameter(
                name="CustomerCardCode",
                label="Customer code",
                type=TEXT,
                required=True,
                max_length=50,
                placeholder="BIC00425",
                help_text=(
                    "SAP customer code, for example BIC00425 (Bio), AGC00589 (Agri) "
                    "or ORC00154 (Orange). Must belong to the company selected "
                    "above. " + _CUSTOMER_CODE_NOTE
                ),
            ),
        ),
    ),
    Report(
        key="4bGeneralLedger",
        label="4b General Ledger",
        description="General ledger movements for a period.",
        authored_company="4B-AGRI_LIVE",
        default_company="4B-AGRI_LIVE",
        notes=(
            "Normally run unfiltered - dates only. The customer filter is "
            "effectively ignored by this report."
        ),
        parameters=(
            _from_date("Start of the ledger period."),
            _to_date("End of the ledger period."),
            Parameter(
                name="CustomerCardCode",
                label="Customer code",
                type=TEXT,
                max_length=50,
                placeholder="AGC00980",
                help_text=(
                    "Leave blank for all customers. This report is normally run "
                    "unfiltered - the customer filter has no visible effect on it."
                ),
            ),
            Parameter(
                name="Region",
                label="Region ID",
                type=INTEGER,
                advanced=True,
                help_text=(
                    "Numeric Region ID from SAP, for example 136 = AGRI GREEN, "
                    "237 = AGRI WHITE, 427 = AGRI BLUE. Not the region name."
                    + _GEO_BROKEN
                ),
            ),
            Parameter(
                name="Zone",
                label="Zone ID",
                type=INTEGER,
                advanced=True,
                help_text=(
                    "Numeric Zone ID, for example 102 = BAHAWALNAGAR, "
                    "201 = ARIF WALA, 25 = BHAKHAR. Not the zone name." + _GEO_BROKEN
                ),
            ),
            Parameter(
                name="Territory",
                label="Territory ID",
                type=INTEGER,
                advanced=True,
                help_text=(
                    "Numeric Territory ID, for example 90 = Ahmad Pur East, "
                    "413 = 18 HAZARI. Not the territory name." + _GEO_BROKEN
                ),
            ),
        ),
    ),
    Report(
        key="CustomerDetailLedgerWithSummary",
        label="Customer Detail Ledger with Summary",
        description="Per-customer statement of account with a summary section.",
        authored_company="4B-AGRI_LIVE",
        default_company="4B-AGRI_LIVE",
        notes=(
            "The customer code is required here: without it the report prints "
            "headings and no rows. The underlying table only holds data from "
            "September 2024, so earlier periods legitimately come back empty."
        ),
        parameters=(
            _from_date(
                "Start of the statement period. This report's data only starts in "
                "September 2024, so earlier dates return nothing."
            ),
            _to_date("End of the statement period."),
            Parameter(
                name="CustomerCardCode",
                label="Customer code",
                type=TEXT,
                required=True,
                max_length=50,
                placeholder="AGC00980",
                help_text=(
                    "SAP customer code, for example AGC00980 (Agri), BIC00038 (Bio) "
                    "or ORC00037 (Orange). Required - without it the report prints "
                    "headings and no rows. " + _CUSTOMER_CODE_NOTE
                ),
            ),
            Parameter(
                name="Region",
                label="Region ID",
                type=INTEGER,
                advanced=True,
                help_text="Numeric Region ID from SAP, not the region name." + _GEO_BROKEN,
            ),
            Parameter(
                name="Zone",
                label="Zone ID",
                type=INTEGER,
                advanced=True,
                help_text="Numeric Zone ID from SAP, not the zone name." + _GEO_BROKEN,
            ),
            Parameter(
                name="Territory",
                label="Territory ID",
                type=INTEGER,
                advanced=True,
                help_text=(
                    "Numeric Territory ID from SAP, not the territory name." + _GEO_BROKEN
                ),
            ),
        ),
    ),
    Report(
        key="BusinessHistory",
        label="Business History",
        description="Trading history for a customer, optionally narrowed to one project.",
        authored_company="4B-AGRI_LIVE",
        default_company="4B-AGRI_LIVE",
        notes=(
            "Run for a single customer for the most detail; left blank it covers "
            "every customer. The project filter takes the project CODE, not its name."
        ),
        parameters=(
            _from_date("Start of the history period."),
            _to_date("End of the history period."),
            Parameter(
                name="CustomerCardCode",
                label="Customer code",
                type=TEXT,
                max_length=50,
                placeholder="AGC00980",
                help_text=(
                    "SAP customer code, for example AGC00980. Leave blank for all "
                    "customers; a single customer produces a short summary. "
                    + _CUSTOMER_CODE_NOTE
                ),
            ),
            Parameter(
                name="Project",
                label="Project code",
                type=TEXT,
                max_length=50,
                placeholder="0223133",
                help_text=(
                    "SAP project CODE - the PrjCode value, for example 0223133 - not "
                    "the project name. Leave blank for all projects."
                ),
            ),
        ),
    ),
    Report(
        key="CollectionDetailReport",
        label="Collection Detail Report",
        description="Collections and receipts recorded in a period.",
        authored_company="4B-AGRI_LIVE",
        default_company="4B-AGRI_LIVE",
        notes=(
            "Normally run unfiltered - dates only. Note that Region, Zone and "
            "Territory are NAMES on this report, not the numeric IDs the ledger "
            "reports expect."
        ),
        parameters=(
            _from_date("Start of the collection period."),
            _to_date("End of the collection period."),
            Parameter(
                name="CustomerCardCode",
                label="Customer code",
                type=TEXT,
                max_length=50,
                help_text=(
                    "Leave blank for all customers. This report is normally run "
                    "unfiltered - the customer filter has no visible effect on it."
                ),
            ),
            # The one report where these three are name strings rather than numeric
            # ids.  Sending a number here produces a Crystal type error.
            Parameter(
                name="Region",
                label="Region name",
                type=TEXT,
                max_length=100,
                advanced=True,
                placeholder="Baluchistan Region",
                help_text=(
                    "Region NAME exactly as spelled in SAP, for example "
                    "'Baluchistan Region'. On this report it is the name, not the "
                    "numeric ID - a number here is rejected." + _GEO_BROKEN
                ),
            ),
            Parameter(
                name="Zone",
                label="Zone name",
                type=TEXT,
                max_length=100,
                advanced=True,
                placeholder="Quetta Zone",
                help_text=(
                    "Zone NAME exactly as spelled in SAP, for example 'Quetta Zone'. "
                    "Not the numeric ID." + _GEO_BROKEN
                ),
            ),
            Parameter(
                name="Territory",
                label="Territory name",
                type=TEXT,
                max_length=100,
                advanced=True,
                placeholder="Ali Pur Territory",
                help_text=(
                    "Territory NAME exactly as spelled in SAP, for example "
                    "'Ali Pur Territory'. Not the numeric ID." + _GEO_BROKEN
                ),
            ),
        ),
    ),
    Report(
        key="ProductLedgerWithSummary",
        label="Product Ledger with Summary",
        description="Stock ledger by item, with a summary section.",
        authored_company="4B-BIO_LIVE",
        default_company="4B-BIO_LIVE",
        notes=(
            "There is no customer filter on this report. It is authored against 4B "
            "Bio and is unlikely to render against another company. Leave the "
            "warehouse blank."
        ),
        parameters=(
            _from_date("Start of the stock period."),
            _to_date("End of the stock period."),
            Parameter(
                name="ItemCode",
                label="Item code",
                type=TEXT,
                max_length=50,
                placeholder="FG00563",
                help_text=(
                    "SAP item code, for example FG00563. Leave blank for a summary "
                    "of all items; enter one item to get its full transaction "
                    "detail. An item with no movements in the period returns "
                    "headings only."
                ),
            ),
            Parameter(
                name="Warehouse",
                label="Warehouse code",
                type=TEXT,
                max_length=20,
                advanced=True,
                danger=True,
                help_text=_WAREHOUSE_WARNING,
            ),
            Parameter(
                name="BatchNo",
                label="Batch number",
                type=TEXT,
                max_length=50,
                advanced=True,
                help_text="SAP batch number. Leave blank for all batches.",
            ),
        ),
    ),
)

REPORTS: Dict[str, Report] = {report.key: report for report in _REPORTS}

# Every parameter name any report accepts, in a stable order. The API exposes
# these as query-string overrides and the admin page renders one box each,
# showing only the ones the selected report actually owns.
QUERY_PARAMETERS: Tuple[str, ...] = tuple(
    dict.fromkeys(spec.name for report in _REPORTS for spec in report.parameters)
)

REPORT_CHOICES: Tuple[Tuple[str, str], ...] = tuple(
    (report.key, report.label) for report in _REPORTS
)


# ---------------------------------------------------------------------------
# Friendly name -> real Crystal prompt name
# ---------------------------------------------------------------------------

# The service resolves friendly names against each .rpt's own parameter list, so
# most names need no help.  These five reports are the exceptions: their designer
# named the prompt just "A", "B", or left it empty before the "@" that introduces
# the list-of-values query.  The resolver refuses to guess between two prompts that
# both normalise to "a" (or to ""), so it returns no match and the service answers
# 400.  Spelling the prompt out here is the documented escape hatch - it hits the
# resolver's exact-ordinal step and wins outright.
#
# These strings are compared byte for byte, with ordinal string comparison.  Do not
# reformat them and do not "tidy" the spacing: BusinessHistory's customer prompt is
# "A@*" with NO space after the "@", while the others are "A@ * ..." with one.  A
# typo cannot silently filter on the wrong field - it fails loudly as a 400 - but it
# will break the report.
#
# The value is a tuple so that one friendly name can fan out to several prompts if a
# future report ever needs it.
CRYSTAL_PARAMETER_ALIASES: Mapping[str, Mapping[str, Tuple[str, ...]]] = {
    "4bGeneralLedger": {
        "CustomerCardCode": ("A@ * FROM OCRD",),
    },
    "CustomerDetailLedgerWithSummary": {
        "CustomerCardCode": ("A@ * FROM OCRD",),
    },
    "BusinessHistory": {
        "CustomerCardCode": ("A@* FROM OCRD WHERE CardType='C'",),
        "Project": ('B@select distinct a."PrjCode",a."PrjName" from OPRJ a',),
    },
    # Two prompts on this report are both named "A" - one for items, one for
    # warehouses - so neither resolves by name alone and the two must not be swapped.
    "ProductLedgerWithSummary": {
        "ItemCode": ("A@ * from oitm",),
        "Warehouse": ("A@ * from owhs",),
    },
    # These three prompts have no name at all before the "@", unlike the same three
    # on the ledger reports, which really are called Region/Zone/Territory and so
    # resolve automatically.
    "CollectionDetailReport": {
        "Region": ('@select distinct a."RegionName" from CWL a',),
        "Zone": ('@select distinct a."ZoneName" from CWL a',),
        "Territory": ('@select distinct a."TerritoryName" from CWL a',),
    },
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def get_report(report_key: str) -> Report:
    """Return the :class:`Report` for ``report_key``.

    Raises ``KeyError`` for an unknown key - callers facing the web should turn
    that into a 404 rather than let it escape.
    """
    try:
        return REPORTS[report_key]
    except KeyError:
        raise KeyError("Unknown report '%s'." % report_key) from None


def iter_reports() -> Iterator[Report]:
    """Reports in display order."""
    return iter(_REPORTS)


def dotnet_format(export_format: str) -> str:
    """Map our lowercase format key onto the service's enum spelling."""
    return DOTNET_FORMAT_NAMES.get(export_format, "Pdf")


def content_type_for(export_format: str) -> str:
    return CONTENT_TYPES.get(export_format, "application/octet-stream")


def filename_for(report_key: str, export_format: str) -> str:
    """Download filename, built from our own extension map.

    Never derive this from the response's Content-Type: the service labels the
    body from the format that was *asked for*, not from what Crystal produced.
    """
    return "%s.%s" % (report_key, FILE_EXTENSIONS.get(export_format, "bin"))


# ---------------------------------------------------------------------------
# Value handling
# ---------------------------------------------------------------------------


def is_blank(value: Any) -> bool:
    """True for values that must be omitted from the request entirely.

    An empty string is a *real* filter value to Crystal (``CardCode = ''``) and
    matches nothing, so an untouched box must drop out of the payload rather than
    be sent as "".  An omitted parameter keeps the report's own default.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def serialize_value(spec: Parameter, value: Any) -> Optional[str]:
    """Render one cleaned form value as the string the service expects.

    Returns ``None`` to mean "omit this key entirely".  Every parameter value goes
    over the wire as a string; the service coerces from there, parsing
    ``YYYY-MM-DD`` back into a date and numeric text into a number for the prompts
    that declare those types.
    """
    if is_blank(value):
        return None

    if spec.type == DATE:
        if isinstance(value, (datetime.datetime, datetime.date)):
            # strftime, not str(): str() on a datetime yields "2024-01-01 00:00:00",
            # which the service will not recognise as a date and will reject.
            return value.strftime("%Y-%m-%d")
        return str(value).strip() or None

    if spec.type == INTEGER:
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
        return str(value).strip() or None

    return str(value).strip() or None


def serialize_parameters(report: Report, values: Mapping[str, Any]) -> Dict[str, str]:
    """Friendly-name payload for ``report``, with blanks dropped.

    Only parameters the report actually owns are kept: sending a prompt a report
    does not have is an immediate 400 from the service.
    """
    payload: Dict[str, str] = {}
    for spec in report.parameters:
        serialized = serialize_value(spec, values.get(spec.name))
        if serialized is not None:
            payload[spec.name] = serialized
    return payload


def resolve_crystal_parameters(
    report_key: str, parameters: Mapping[str, str]
) -> Dict[str, str]:
    """Apply the per-report alias table: friendly name -> real prompt name.

    Run this last, after blanks have been dropped and values stringified, and keep
    the friendly-named dict for logging - the aliased names are unreadable.
    Anything without an alias passes through unchanged and is resolved against the
    report's own parameter list on the service side.
    """
    aliases = CRYSTAL_PARAMETER_ALIASES.get(report_key, {})
    resolved: Dict[str, str] = {}
    for name, value in parameters.items():
        for crystal_name in aliases.get(name, (name,)):
            resolved[crystal_name] = value
    return resolved


# ---------------------------------------------------------------------------
# Self-check - runs at import so that a typo in the tables above fails immediately,
# rather than much later as a 400 from a remote service.
# ---------------------------------------------------------------------------


def _validate_registry() -> None:
    format_values = set(EXPORT_FORMAT_VALUES)

    for report in _REPORTS:
        prefix = "Report '%s'" % report.key

        if not report.formats:
            raise ValueError("%s offers no export formats." % prefix)
        unknown_formats = set(report.formats) - format_values
        if unknown_formats:
            raise ValueError(
                "%s offers unknown export format(s): %s."
                % (prefix, ", ".join(sorted(unknown_formats)))
            )
        if report.default_format not in report.formats:
            raise ValueError(
                "%s defaults to format '%s', which it does not offer."
                % (prefix, report.default_format)
            )
        if report.default_company and report.default_company not in ALLOWED_COMPANIES:
            raise ValueError(
                "%s defaults to company '%s', which is not in the allow-list."
                % (prefix, report.default_company)
            )
        if report.authored_company and report.authored_company not in ALLOWED_COMPANIES:
            raise ValueError(
                "%s is authored against unknown company '%s'."
                % (prefix, report.authored_company)
            )

        seen = set()
        for spec in report.parameters:
            if spec.type not in FIELD_TYPES:
                raise ValueError(
                    "%s parameter '%s' has unknown type '%s'."
                    % (prefix, spec.name, spec.type)
                )
            if spec.name in seen:
                raise ValueError(
                    "%s declares parameter '%s' twice." % (prefix, spec.name)
                )
            seen.add(spec.name)

    for report_key, aliases in CRYSTAL_PARAMETER_ALIASES.items():
        if report_key not in REPORTS:
            raise ValueError("Alias table references unknown report '%s'." % report_key)
        known = set(REPORTS[report_key].parameter_names)
        for friendly_name, crystal_names in aliases.items():
            if friendly_name not in known:
                raise ValueError(
                    "Alias table maps '%s' on report '%s', which has no such parameter."
                    % (friendly_name, report_key)
                )
            if not isinstance(crystal_names, tuple) or not crystal_names:
                raise ValueError(
                    "Alias for '%s' on report '%s' must be a non-empty tuple."
                    % (friendly_name, report_key)
                )


_validate_registry()

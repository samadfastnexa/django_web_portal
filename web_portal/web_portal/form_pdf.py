"""
Paper-form PDF for the Field Activities data-entry records.

Renders a record the way the printed data-entry sheet looks - a Field /
Description table for the header details, then a numbered attendee table:

    FIELD DAY-DATA ENTRY

    +----------------------+----------------------------+
    | Field                | Description                |
    +----------------------+----------------------------+
    | Date                 | 12-Jun-2026 10:30          |
    | Total Attendees      | 42                         |
    | ...                  | ...                        |
    +----------------------+----------------------------+

    Field Day:

    +-----+-------------+----------------+---------+-------+
    | SR #| Farmer Name | Contact Number | Acreage | Crop  |
    +-----+-------------+----------------+---------+-------+
    | 1   | Allah Ditta | 0300-1234567   | 12.5    | Wheat |

One record per page. Meeting / FieldDay / MeetingSchedule share it - the same
sheet with different field lists - while HPMRequisition keeps its own layout in
`farmerMeetingDataEntry.hpm_report`, because its approval and signature block
has no equivalent here. Both feed `render_pdf_response()`, so a bulk export is
one PDF regardless of which form produced the pages.

Greyscale like the printed sheet; override `settings.FORM_PDF_COLORS` to
re-theme without editing this module.
"""
import datetime
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone

#: The attendee table is identical on every one of these sheets.
ATTENDEE_COLUMNS = ('SR #', 'Farmer Name', 'Contact Number', 'Acreage', 'Crop')
#: mm, summing to the 174mm A4 portrait content width left by the margins below.
ATTENDEE_WIDTHS = (15, 55, 45, 25, 34)

DEFAULT_COLORS = {
    'header_bg': '#D9D9D9',   # the grey "Field | Description" band
    'header_fg': '#000000',
    'grid': '#000000',
    'text': '#000000',
}


def form_colors():
    """Palette, settings winning over the greyscale defaults."""
    colors = dict(DEFAULT_COLORS)
    override = getattr(settings, 'FORM_PDF_COLORS', None)
    if isinstance(override, dict):
        for key, value in override.items():
            if key in colors and isinstance(value, str) and value.strip():
                colors[key] = value.strip()
    return colors


# ---------------------------------------------------------------- formatting


def fmt_datetime(value):
    """'12-Jun-2026 10:30' for a datetime, plain date for a DateField."""
    if not value:
        return ''
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%d-%b-%Y %H:%M')
    return value.strftime('%d-%b-%Y')


def fmt_number(value):
    """12.0 -> '12', 12.5 -> '12.5'. Keeps acreage cells from reading '12.0'."""
    if value in (None, ''):
        return ''
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number == int(number) else f'{number:g}'


def fmt_yesno(value):
    return 'Yes' if value else 'No'


def fmt_person(user):
    """Display name for a user cell, falling back to username / email."""
    if not user:
        return ''
    full = f'{user.first_name or ""} {user.last_name or ""}'.strip()
    return full or user.get_username() or (user.email or '')


def attendee_rows(attendees):
    """Attendee queryset -> [SR #, Name, Contact, Acreage, Crop] rows.

    One row per attendee, not per crop, so the SR # column still counts
    farmers. Where the newer `crops` relation is populated it wins over the
    legacy single `crop`/`acreage` pair, and the acreages are summed.
    """
    rows = []
    for index, attendee in enumerate(attendees, 1):
        crops = list(getattr(attendee, 'crops', None).all()) if hasattr(attendee, 'crops') else []
        if crops:
            crop = ', '.join(c.crop_name for c in crops if c.crop_name)
            acreage = sum(c.acreage or 0 for c in crops)
        else:
            crop = attendee.crop or ''
            acreage = attendee.acreage or 0
        rows.append([
            str(index),
            attendee.farmer_name or '',
            attendee.contact_number or '',
            fmt_number(acreage),
            crop,
        ])
    return rows


# ------------------------------------------------------------------ building


def form_story(title, fields, table_heading=None, columns=(), col_widths=(),
               rows=(), min_rows=10):
    """Flowables for one record's sheet.

    `fields` is a list of (label, value) pairs for the Field / Description
    table. `columns` / `rows` are the attendee table below it, padded out to
    `min_rows` so a sparsely attended meeting still prints as a usable form.
    """
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    palette = form_colors()

    def hexc(key):
        try:
            return rl_colors.HexColor(palette[key])
        except Exception:
            return rl_colors.HexColor(DEFAULT_COLORS[key])

    text_color = hexc('text')
    body = ParagraphStyle('body', fontName='Helvetica', fontSize=9, leading=12,
                          textColor=text_color)
    bold = ParagraphStyle('bold', parent=body, fontName='Helvetica-Bold')
    doc_title = ParagraphStyle('doc_title', parent=bold, fontSize=10, leading=13)
    section = ParagraphStyle('section', fontName='Helvetica', fontSize=20,
                             leading=24, textColor=text_color)

    def para(value, style=body):
        # Paragraph rather than a bare string so long topics/feedback wrap
        # inside the cell instead of running off the page. Escape first -
        # reportlab parses the text as mini-HTML, so an "&" or "<" typed into
        # feedback would otherwise abort the whole document.
        text = escape(str(value if value is not None else ''))
        return Paragraph(text.replace('\n', '<br/>'), style)

    # No ALIGN commands here: every cell holds a Paragraph, which honours its
    # own style's alignment and ignores the table's.
    grid = [
        ('GRID', (0, 0), (-1, -1), 0.75, hexc('grid')),
        ('BACKGROUND', (0, 0), (-1, 0), hexc('header_bg')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]

    header_style = ParagraphStyle('header', parent=bold, alignment=1,
                                  textColor=hexc('header_fg'))
    centered = ParagraphStyle('centered', parent=body, alignment=1)

    story = [Paragraph(title, doc_title), Spacer(1, 7 * mm)]

    # --- Field / Description ------------------------------------------------
    detail_rows = [[para('Field', header_style), para('Description', header_style)]]
    detail_rows += [[para(label, bold), para(value)] for label, value in fields]
    details = Table(detail_rows, colWidths=[50 * mm, 100 * mm], repeatRows=1,
                    hAlign='LEFT')
    details.setStyle(TableStyle(grid))
    story.append(details)

    if not columns:
        return story

    # --- attendee table -----------------------------------------------------
    story += [Spacer(1, 10 * mm), Paragraph(table_heading or '', section),
              Spacer(1, 4 * mm)]

    padded = [list(row) for row in rows]
    # Blank lines keep the printed sheet usable when attendees were not
    # captured in the portal - the same reason the paper form ships with them.
    for index in range(len(padded) + 1, min_rows + 1):
        padded.append([str(index)] + [''] * (len(columns) - 1))

    # First column is the SR #, centred under its header as on the paper form.
    body_rows = [
        [para(cell, centered if index == 0 else body)
         for index, cell in enumerate(row)]
        for row in padded
    ]
    table = Table(
        [[para(c, header_style) for c in columns]] + body_rows,
        colWidths=[w * mm for w in col_widths] or None,
        repeatRows=1,
        hAlign='LEFT',
    )
    table.setStyle(TableStyle(grid))
    story.append(table)
    return story


def render_pdf_response(stories, filename, title=None, margin=18):
    """Join per-record stories with page breaks into one downloadable PDF.

    `margin` is in mm; hpm_report passes a narrower one because its tables are
    laid out for a wider content area than these sheets.
    """
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer

    flowables = []
    for index, story in enumerate(stories):
        if index:
            flowables.append(PageBreak())
        flowables.extend(story)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=margin * mm, rightMargin=margin * mm,
        topMargin=margin * mm, bottomMargin=margin * mm,
        title=title or filename,
    )
    # An empty story raises out of reportlab; ship a blank page instead so the
    # action never 500s on an empty selection.
    doc.build(flowables or [Spacer(1, 1 * mm)])

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def form_pdf_action(build_story, description, filename_prefix, name=None, margin=18):
    """Build an admin action that exports the selection as form-style PDFs.

    `build_story(obj)` returns the flowables for one record - normally a
    `form_story(...)` call.
    """
    @admin.action(description=description)
    def export_pdf(model_admin, request, queryset):
        stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        return render_pdf_response(
            [build_story(obj) for obj in queryset],
            f'{filename_prefix}_{stamp}.pdf',
            title=description,
            margin=margin,
        )

    export_pdf.__name__ = name or f'export_{filename_prefix}_pdf'
    return export_pdf

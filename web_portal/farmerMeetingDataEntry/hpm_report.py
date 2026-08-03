"""
Printable PDF of a single HPM requisition, laid out like the paper form.

    +-------------------------------------------------------------------+
    |        HIGH-PROFILE FARMER MEETING FOR GM/BM                      |
    |                  REQUISITION FORM                                 |
    +------------------+----------------+------------+------------------+
    | Requisition Date | 2026-07-30     | GM/BM Name | Asif Saeed       |
    +------------------+----------------+------------+------------------+
    |                     HPM MEETING DETAILS                           |
    | Zone / Region / Territory / Responsible Person / ...              |
    +-------------------------------------------------------------------+
    |                       APPROVAL SECTION                            |
    | GM/BM Signature | <name>        | Date | 2026-07-30               |
    | CEO Remarks     | ...                                             |
    | CEO Signature   | <name>        | Date | 2026-07-31               |
    +-------------------------------------------------------------------+

Signatures are *recorded, not drawn*: the cells print the responsible person's
name and the timestamp that was stamped when they submitted or decided, so the
document is auditable without handling signature images.

Colours resolve from settings / a preferences.Setting row - same layering as
attendance.reports.report_colors() - so the sheet can be re-themed without
editing this module.
"""
import datetime
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone

#: Slug of the admin-editable preferences.Setting row holding the palette.
COLOR_SETTING_SLUG = 'hpm_requisition_colors'

DEFAULT_COLORS = {
    'title_fg': '#000000',
    'section_bg': '#4472C4',   # the blue "HPM MEETING DETAILS" band
    'section_fg': '#FFFFFF',
    'approval_bg': '#595959',  # the grey "APPROVAL SECTION" band
    'approval_fg': '#FFFFFF',
    'label_bg': '#D9D9D9',     # left-hand label column
    'label_fg': '#000000',
    'value_bg': '#FFFFFF',
    'value_fg': '#000000',
    'grid': '#7F7F7F',
}


def _apply(colors, override):
    if not isinstance(override, dict):
        return
    for key, value in override.items():
        if key in colors and isinstance(value, str) and value.strip():
            colors[key] = value.strip()


def report_colors():
    """Palette, most specific source winning: Setting row > settings.py > default."""
    colors = dict(DEFAULT_COLORS)
    _apply(colors, getattr(settings, 'HPM_REQUISITION_COLORS', None))
    try:
        from preferences.models import Setting
        row = Setting.objects.filter(slug=COLOR_SETTING_SLUG, is_active=True).first()
        if row:
            _apply(colors, row.get_value())
    except Exception:
        # Missing table (pre-migrate) or db down - fall back to code defaults.
        pass
    return colors


def _person(user):
    """Display name for a signature cell."""
    if not user:
        return ''
    full = f'{user.first_name or ""} {user.last_name or ""}'.strip()
    return full or user.get_username() or (user.email or '')


def _date(value):
    """Date only. Accepts a date or a datetime.

    `requisition_date` / `meeting_date` are DateFields, so the value is a plain
    `date` - `timezone.is_aware()` would blow up on it (no `utcoffset`). Only
    localise when there is actually a time component.
    """
    if not value:
        return ''
    if isinstance(value, datetime.datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%d-%b-%Y')


def _stamp(value):
    """Date + time for a signature stamp; date alone for a plain DateField."""
    if not value:
        return ''
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%d-%b-%Y %H:%M')
    return value.strftime('%d-%b-%Y')


#: Narrower than the data-entry sheets in web_portal.form_pdf - the tables
#: below are laid out for a 182mm content width.
PAGE_MARGIN_MM = 14


def requisition_story(obj):
    """Flowables for one requisition, ready to drop into a document.

    Split out from `render_requisition_pdf` so the changelist action can put
    several requisitions in one PDF without re-implementing the layout.
    """
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    palette = report_colors()

    def hexc(key):
        try:
            return rl_colors.HexColor(palette[key])
        except Exception:
            return rl_colors.HexColor(DEFAULT_COLORS[key])

    # Paragraph cells carry their own colour - the table's TEXTCOLOR commands
    # only reach plain-string cells, so the palette is applied on the styles.
    body = ParagraphStyle('body', fontName='Helvetica', fontSize=8.5, leading=11,
                          textColor=hexc('value_fg'))
    title = ParagraphStyle(
        'title', fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=1,
    )
    subtitle = ParagraphStyle(
        'subtitle', fontName='Helvetica-Bold', fontSize=10.5, leading=13, alignment=1,
    )

    label_style = ParagraphStyle('label', parent=body, fontName='Helvetica-Bold',
                                 textColor=hexc('label_fg'))

    def para(text, style=body):
        # Paragraph so long purpose/remarks wrap instead of overflowing the
        # cell. Escaped first because reportlab reads the text as mini-HTML -
        # an "&" typed into remarks would otherwise abort the document.
        return Paragraph(escape(str(text or '')).replace('\n', '<br/>'), style)

    def label(text):
        # The long "Purpose of Meeting (...)" label runs past the 58mm label
        # column as a bare string, printing over the value beside it.
        return para(text, label_style)

    label_w, value_w = 58 * mm, 123 * mm

    # --- header: Requisition Date | GM/BM Name ---------------------------
    header = Table(
        [['Requisition Date', _date(obj.requisition_date),
          'GM/BM Name', para(_person(obj.submitted_by))]],
        colWidths=[34 * mm, 56 * mm, 30 * mm, 61 * mm],
    )
    header.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, hexc('grid')),
        ('BACKGROUND', (0, 0), (0, 0), hexc('label_bg')),
        ('BACKGROUND', (2, 0), (2, 0), hexc('label_bg')),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    # --- HPM meeting details --------------------------------------------
    detail_rows = [
        ['HPM MEETING DETAILS', ''],
        [label('Zone'), para(obj.zone_fk.name if obj.zone_fk else '')],
        [label('Region'), para(obj.region_fk.name if obj.region_fk else '')],
        [label('Territory'), para(obj.territory_fk.name if obj.territory_fk else '')],
        [label('Responsible Person'), para(_person(obj.responsible_person))],
        # _stamp, not _date: meeting_date is a DateTimeField, so print the time.
        [label('Meeting Date & Time'), _stamp(obj.meeting_date)],
        [label('Meeting Location'), para(obj.meeting_location)],
        [label('No. of Farmers / Attendees'), str(obj.expected_attendees or 0)],
        [label('Purpose of Meeting (Product Related Campaign & Sale Commitment)'),
         para(obj.purpose)],
        [label('Remarks'), para(obj.remarks)],
    ]
    details = Table(detail_rows, colWidths=[label_w, value_w])
    details.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, hexc('grid')),
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (1, 0), hexc('section_bg')),
        ('TEXTCOLOR', (0, 0), (1, 0), hexc('section_fg')),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('BACKGROUND', (0, 1), (0, -1), hexc('label_bg')),
        ('TEXTCOLOR', (0, 1), (0, -1), hexc('label_fg')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (1, 1), (1, -1), hexc('value_bg')),
        ('TEXTCOLOR', (1, 1), (1, -1), hexc('value_fg')),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    # --- approval section -------------------------------------------------
    approval_rows = [
        ['APPROVAL SECTION', '', '', ''],
        ['GM/BM Signature:', para(_person(obj.submitted_by)),
         'Date:', _stamp(obj.submitted_at)],
        ['CEO Remarks:', para(obj.ceo_remarks), '', ''],
        ['CEO Signature:', para(_person(obj.reviewed_by)),
         'Date:', _stamp(obj.reviewed_at)],
        ['Status:', obj.get_status_display(), '', ''],
    ]
    approval = Table(
        approval_rows,
        colWidths=[38 * mm, 73 * mm, 18 * mm, 52 * mm],
        rowHeights=[None, 14 * mm, 20 * mm, 14 * mm, None],
    )
    approval.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, hexc('grid')),
        ('SPAN', (0, 0), (3, 0)),
        ('BACKGROUND', (0, 0), (3, 0), hexc('approval_bg')),
        ('TEXTCOLOR', (0, 0), (3, 0), hexc('approval_fg')),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (3, 0), 'CENTER'),
        # CEO remarks and Status stretch across the value columns.
        ('SPAN', (1, 2), (3, 2)),
        ('SPAN', (1, 4), (3, 4)),
        ('BACKGROUND', (0, 1), (0, -1), hexc('label_bg')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))

    note = Paragraph(
        '<i>Note: This form should be filled by the concerned GM/BM and submitted '
        'for CEO approval before arranging the meeting.</i>',
        ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=7.5,
                       leading=10, alignment=1),
    )

    return [
        Paragraph('HIGH-PROFILE FARMER MEETING FOR GM/BM', title),
        Spacer(1, 3 * mm),
        Paragraph('REQUISITION FORM', subtitle),
        Spacer(1, 6 * mm),
        header,
        Spacer(1, 6 * mm),
        details,
        Spacer(1, 8 * mm),
        approval,
        Spacer(1, 4 * mm),
        note,
    ]


def render_requisition_pdf(obj, filename=None):
    """One requisition as a print-ready A4 portrait PDF."""
    from web_portal.form_pdf import render_pdf_response

    return render_pdf_response(
        [requisition_story(obj)],
        filename or f'hpm-requisition-{obj.pk}.pdf',
        title=f'HPM Requisition {obj.pk}',
        margin=PAGE_MARGIN_MM,
    )

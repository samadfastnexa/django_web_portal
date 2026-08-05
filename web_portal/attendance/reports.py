"""
Attendance Report - PDF and CSV, in the printed sheet's column order.

Layout matches the spreadsheet the field team uses:

    +---------------------------------------------------+-----------+
    |               Attendance Report                    |  24-Apr   |
    +--------+------+-----------+---------+--------------+-----------+
    | Region | Zone | Territory | Joining | ... | Status | CheckIn   |
    +--------+------+-----------+---------+--------------+-----------+

One row per active sales-staff member for the reporting scope, so the Status
column is meaningful: staff with a check-in are Present, staff with an approved
LeaveRequest covering the date are On Leave, everyone else is Absent.

Every colour comes from settings.ATTENDANCE_REPORT_COLORS - see report_colors().
"""
import csv
import datetime
import io
import os

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone

# Column order is the contract with the printed sheet - do not reorder.
# Photo is appended rather than inserted so the original order is untouched.
COLUMNS = [
    'Region',
    'Zone',
    'Territory',
    'Joining Date',
    'Designation',
    'File No',
    'Employee Name',
    'Status',
    'CheckIn Time',
    'Photo',
]

# Headings painted with the secondary colour (the peach block on the sheet).
ALT_HEADER_COLUMNS = {'Status', 'CheckIn Time', 'Photo'}

# Thumbnail box in the PDF, in mm. Images are scaled to fit, never stretched.
PHOTO_BOX_MM = (16, 16)
# Pixel ceiling the photo is downsampled to before embedding. 16mm at ~300dpi
# is ~190px, so this prints cleanly while keeping the PDF small.
PHOTO_MAX_PX = (200, 200)

DEFAULT_COLORS = {
    'title_bg': '#F2F2F2',
    'title_fg': '#000000',
    'date_bg': '#E2EFDA',
    'date_fg': '#000000',
    'header_bg': '#FFFF00',
    'header_fg': '#000000',
    'header_alt_bg': '#FCE4D6',
    'header_alt_fg': '#000000',
    'row_bg': '#FFFFFF',
    'row_alt_bg': '#F7F7F7',
    'row_fg': '#000000',
    'grid': '#808080',
}

STATUS_PRESENT = 'Present'
STATUS_LEAVE = 'On Leave'
STATUS_ABSENT = 'Absent'


#: Slug of the admin-editable preferences.Setting row holding the palette.
COLOR_SETTING_SLUG = 'attendance_report_colors'


def _apply(colors, override):
    """Copy recognised hex values from `override` onto `colors`, in place."""
    if not isinstance(override, dict):
        return
    for key, value in override.items():
        if key in colors and isinstance(value, str) and value.strip():
            colors[key] = value.strip()


def report_colors():
    """Palette for the report, most specific source winning.

        1. preferences.Setting slug 'attendance_report_colors'  (edit in admin)
        2. settings.ATTENDANCE_REPORT_COLORS                    (edit in code)
        3. DEFAULT_COLORS

    Merged per key, so a partial override is fine and one bad value cannot
    break rendering. The Setting row is what non-developers change - see
    ensure_color_setting().
    """
    colors = dict(DEFAULT_COLORS)
    _apply(colors, getattr(settings, 'ATTENDANCE_REPORT_COLORS', None))
    try:
        from preferences.models import Setting
        row = Setting.objects.filter(slug=COLOR_SETTING_SLUG, is_active=True).first()
        if row:
            _apply(colors, row.get_value())
    except Exception:
        # Missing table (pre-migrate), db down - fall back to code defaults.
        pass
    return colors


def ensure_color_setting():
    """Create the admin-editable palette row if it does not exist yet.

    Without a row there is nothing to find under Settings, which is exactly the
    confusion this avoids: the theme is visible and editable in the admin.
    """
    from preferences.models import Setting

    row, created = Setting.objects.get_or_create(
        slug=COLOR_SETTING_SLUG,
        user=None,
        defaults={'value': dict(DEFAULT_COLORS), 'is_active': True},
    )
    return row, created


def _primary_name(manager):
    """First related name, with a "+N" tail when the staff member covers more.

    The sheet has one cell per level, but a national manager can be attached to
    ~50 territories; spelling them all out would blow the column apart. `.name`
    is used rather than str(), whose __str__ appends the company in brackets.
    """
    try:
        items = list(manager.all())
    except Exception:
        return '-'
    if not items:
        return '-'
    first = getattr(items[0], 'name', None) or str(items[0])
    return f'{first} +{len(items) - 1}' if len(items) > 1 else first


def _shorten(value):
    """A comma-separated list as "first +N" - the sheet has one narrow cell per level.

    Mirrors _primary_name's presentation so stamped and profile-derived rows read
    the same, and keeps a national manager's ~130 territories from blowing the
    column apart.
    """
    parts = [p.strip() for p in str(value or '').split(',') if p.strip()]
    if not parts:
        return '-'
    return f'{parts[0]} +{len(parts) - 1}' if len(parts) > 1 else parts[0]


def _employee_name(user):
    full = f'{user.first_name or ""} {user.last_name or ""}'.strip()
    return full or user.get_username() or (user.email or '-')


def _fmt_date(value):
    if not value:
        return '-'
    if timezone.is_aware(value) if isinstance(value, datetime.datetime) else False:
        value = timezone.localtime(value)
    return value.strftime('%d-%b-%Y')


def _image_name(field):
    """Storage name behind an ImageField, or '' when unset."""
    try:
        return field.name or ''
    except Exception:
        return ''


def image_path(name):
    """Absolute path for a stored image, or None if it is missing/unreadable.

    Rows can reference an image whose file is no longer on disk (common after a
    media restore), so every caller must tolerate None rather than raise.
    """
    if not name or name == '-':
        return None
    try:
        from django.core.files.storage import default_storage
        try:
            path = default_storage.path(name)
        except (NotImplementedError, AttributeError):
            path = os.path.join(str(settings.MEDIA_ROOT), name)
        return path if os.path.isfile(path) else None
    except Exception:
        return None


def _fmt_time(value):
    if not value:
        return '-'
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%d-%b-%Y %H:%M')


def build_rows(attendance_qs, report_date=None, only_users=None, period=None):
    """Report rows for every active sales-staff member, ordered by hierarchy.

    `attendance_qs` is the scope of attendance already selected in the admin
    (its filters decide who counts as Present). `report_date` drives the leave
    lookup and defaults to today.

    `only_users` limits the sheet to those user ids - without it a single-person
    report would still list every colleague as Absent. `period` is an inclusive
    (start, end) pair for a multi-day sheet: someone counts as on leave if their
    approved leave overlaps the range anywhere, not just on `report_date`.
    """
    from django.contrib.auth import get_user_model
    from .models import LeaveRequest

    User = get_user_model()
    report_date = report_date or timezone.localdate()
    start, end = period or (report_date, report_date)

    # Earliest check-in per attendee inside the scope, with the selfie taken
    # at that check-in (the photo that actually evidences the attendance).
    check_in_by_user = {}
    photo_by_user = {}
    rows_in_scope = attendance_qs.values_list(
        'attendee_id', 'check_in_time', 'check_in_image'
    )
    for attendee_id, check_in, photo in rows_in_scope:
        if attendee_id is None:
            continue
        current = check_in_by_user.get(attendee_id)
        is_earlier = check_in and (current is None or check_in < current)
        if is_earlier or attendee_id not in check_in_by_user:
            check_in_by_user[attendee_id] = check_in if is_earlier else current
            if photo:
                photo_by_user[attendee_id] = photo

    # Where each person worked, taken from the attendance row itself so a report
    # of last year's attendance shows last year's posting. Rows in scope win;
    # absentees have none, so their most recent stamp is used, and only then the
    # profile's own assignments.
    location_by_user = {}
    for attendee_id, region, zone, territory in attendance_qs.values_list(
            'attendee_id', 'region', 'zone', 'territory'):
        if attendee_id is not None and attendee_id not in location_by_user \
                and (region or zone or territory):
            location_by_user[attendee_id] = (region, zone, territory)

    on_leave = set(
        LeaveRequest.objects.filter(
            status=LeaveRequest.STATUS_APPROVED,
            start_date__lte=end,
            end_date__gte=start,
        ).values_list('user_id', flat=True)
    )

    # Active sales staff are who the sheet EXPECTS - they are the pool the
    # Present/Absent split is measured against. Anyone who actually marked
    # attendance in scope is added on top, even if they fall outside that pool:
    # their record is visible on the changelist, so leaving them off made those
    # rows impossible to export and the sheet look broken.
    staff = (
        User.objects.filter(
            Q(is_active=True, is_sales_staff=True, is_superuser=False)
            | Q(pk__in=set(check_in_by_user))
        )
        .distinct()
        .select_related('sales_profile', 'sales_profile__designation')
        .prefetch_related(
            'sales_profile__regions', 'sales_profile__zones', 'sales_profile__territories'
        )
    )
    if only_users is not None:
        staff = staff.filter(pk__in=list(only_users))

    missing = [u.pk for u in staff if u.pk not in location_by_user]
    if missing:
        from .models import Attendance
        latest = (
            Attendance.objects.filter(attendee_id__in=missing)
            .exclude(region__isnull=True, zone__isnull=True, territory__isnull=True)
            .order_by('attendee_id', '-id')
            .values_list('attendee_id', 'region', 'zone', 'territory')
        )
        for attendee_id, region, zone, territory in latest:
            location_by_user.setdefault(attendee_id, (region, zone, territory))

    rows = []
    for user in staff:
        profile = getattr(user, 'sales_profile', None)
        if user.pk in check_in_by_user:
            status = STATUS_PRESENT
            check_in = _fmt_time(check_in_by_user[user.pk])
        elif user.pk in on_leave:
            status, check_in = STATUS_LEAVE, '-'
        else:
            status, check_in = STATUS_ABSENT, '-'

        # Check-in selfie is the attendance evidence; fall back to the staff
        # member's profile photo so absentees still show a face on the sheet.
        photo = photo_by_user.get(user.pk) or _image_name(user.profile_image)

        stamped = location_by_user.get(user.pk)
        if stamped:
            region_cell, zone_cell, territory_cell = (_shorten(v) for v in stamped)
        else:
            region_cell = _primary_name(profile.regions) if profile else '-'
            zone_cell = _primary_name(profile.zones) if profile else '-'
            territory_cell = _primary_name(profile.territories) if profile else '-'

        rows.append([
            region_cell,
            zone_cell,
            territory_cell,
            _fmt_date(user.date_joined),
            str(profile.designation) if profile and profile.designation_id else '-',
            (profile.employee_code if profile else '') or '-',
            _employee_name(user),
            status,
            check_in,
            photo or '-',
        ])

    # Group the sheet the way it is read: Region, then Zone, Territory, name.
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[6]))
    return rows


def render_csv(rows, date_label, filename='attendance-report.csv'):
    """CSV mirroring the sheet, banner row included so both formats match."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('﻿')  # BOM so Excel opens UTF-8 correctly
    writer = csv.writer(response)
    writer.writerow(['Attendance Report', date_label])
    writer.writerow([])
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return response


# Column widths for the Excel sheet, in characters. CSV carries no formatting
# at all, so a spreadsheet opened from one shows every column at the default
# width - this is the format to hand someone who wants to read the sheet rather
# than import it.
XLSX_WIDTHS = {
    'Region': 24, 'Zone': 24, 'Territory': 32, 'Joining Date': 14,
    'Designation': 30, 'File No': 12, 'Employee Name': 28, 'Status': 12,
    'CheckIn Time': 20, 'Photo': 42,
}


def render_xlsx(rows, date_label, filename='attendance-report.xlsx'):
    """The sheet as a real spreadsheet: sized columns, frozen header, filters."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    colors = report_colors()

    def fill(key):
        return PatternFill('solid', start_color=colors[key].lstrip('#').upper())

    def font(key, **kw):
        return Font(color=colors[key].lstrip('#').upper(), **kw)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Attendance'
    last = len(COLUMNS)

    ws.cell(1, 1, 'Attendance Report').font = font('title_fg', bold=True, size=14)
    ws.cell(1, 1).fill = fill('title_bg')
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(last - 3, 1))
    ws.cell(1, max(last - 2, 1), date_label).font = font('date_fg', bold=True)
    ws.cell(1, max(last - 2, 1)).fill = fill('date_bg')
    ws.merge_cells(start_row=1, start_column=max(last - 2, 1), end_row=1, end_column=last)
    ws.row_dimensions[1].height = 22

    thin = Side(style='thin', color=colors['grid'].lstrip('#').upper())
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col, name in enumerate(COLUMNS, 1):
        alt = name in ALT_HEADER_COLUMNS
        cell = ws.cell(3, col, name)
        cell.fill = fill('header_alt_bg' if alt else 'header_bg')
        cell.font = font('header_alt_fg' if alt else 'header_fg', bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(col)].width = XLSX_WIDTHS.get(name, 18)

    for offset, row in enumerate(rows):
        shade = fill('row_alt_bg' if offset % 2 else 'row_bg')
        for col, value in enumerate(row[:last], 1):
            cell = ws.cell(4 + offset, col, value)
            cell.fill = shade
            cell.font = font('row_fg')
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            cell.border = border

    ws.freeze_panes = 'A4'
    if rows:
        ws.auto_filter.ref = f'A3:{get_column_letter(last)}{3 + len(rows)}'

    buffer = io.BytesIO()
    wb.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def render_pdf(rows, date_label, filename='attendance-report.pdf'):
    """Landscape PDF laid out like the printed sheet, coloured from settings."""
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image as RLImage, SimpleDocTemplate, Table, TableStyle

    palette = report_colors()
    box_w, box_h = PHOTO_BOX_MM[0] * mm, PHOTO_BOX_MM[1] * mm

    def photo_cell(name):
        """Scaled thumbnail flowable, or '' when the file is missing/unreadable.

        The source photo is downsampled before it goes into the PDF. reportlab
        otherwise embeds the original bytes at full camera resolution, which
        turned an 11-row report into a 4 MB file.
        """
        path = image_path(name)
        if not path:
            return ''
        try:
            from PIL import Image as PILImage

            with PILImage.open(path) as img:
                img.load()
                if img.mode not in ('RGB', 'L'):
                    # Flatten alpha onto white so PNG selfies don't go black.
                    background = PILImage.new('RGB', img.size, (255, 255, 255))
                    rgba = img.convert('RGBA')
                    background.paste(rgba, mask=rgba.split()[-1])
                    img = background
                else:
                    img = img.convert('RGB')
                img.thumbnail(PHOTO_MAX_PX, PILImage.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=72, optimize=True)
            buf.seek(0)
            width, height = ImageReader(buf).getSize()
            if not width or not height:
                return ''
            scale = min(box_w / width, box_h / height)
            buf.seek(0)
            return RLImage(buf, width=width * scale, height=height * scale)
        except Exception:
            # Unsupported/corrupt file - leave the cell blank rather than fail
            # the whole report.
            return ''

    def hexc(key):
        try:
            return rl_colors.HexColor(palette[key])
        except Exception:
            return rl_colors.HexColor(DEFAULT_COLORS[key])

    last = len(COLUMNS) - 1
    alt_start = min(
        (i for i, name in enumerate(COLUMNS) if name in ALT_HEADER_COLUMNS),
        default=last + 1,
    )

    # Row 0 is the banner: title spans the primary headings, date spans the rest.
    banner = [''] * len(COLUMNS)
    banner[0] = 'Attendance Report'
    banner[alt_start if alt_start <= last else last] = date_label

    # Swap the trailing photo path for an embedded thumbnail.
    body = []
    for row in (rows or [['-'] * len(COLUMNS)]):
        row = list(row)
        if len(row) == len(COLUMNS):
            row[-1] = photo_cell(row[-1])
        body.append(row)
    data = [banner, list(COLUMNS)] + body

    style = [
        ('GRID', (0, 0), (-1, -1), 0.5, hexc('grid')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # 7pt left the wider columns looking half empty and was hard to read at
        # arm's length; 8pt still fits the same rows per page.
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        # banner
        ('SPAN', (0, 0), (max(alt_start - 1, 0), 0)),
        ('BACKGROUND', (0, 0), (max(alt_start - 1, 0), 0), hexc('title_bg')),
        ('TEXTCOLOR', (0, 0), (max(alt_start - 1, 0), 0), hexc('title_fg')),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 0), 12),
        ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
        # headings
        ('BACKGROUND', (0, 1), (alt_start - 1, 1), hexc('header_bg')),
        ('TEXTCOLOR', (0, 1), (alt_start - 1, 1), hexc('header_fg')),
        ('TEXTCOLOR', (0, 2), (-1, -1), hexc('row_fg')),
    ]
    if alt_start <= last:
        style += [
            ('SPAN', (alt_start, 0), (last, 0)),
            ('BACKGROUND', (alt_start, 0), (last, 0), hexc('date_bg')),
            ('TEXTCOLOR', (alt_start, 0), (last, 0), hexc('date_fg')),
            ('BACKGROUND', (alt_start, 1), (last, 1), hexc('header_alt_bg')),
            ('TEXTCOLOR', (alt_start, 1), (last, 1), hexc('header_alt_fg')),
        ]
    for offset in range(len(data) - 2):
        shade = 'row_alt_bg' if offset % 2 else 'row_bg'
        style.append(('BACKGROUND', (0, offset + 2), (-1, offset + 2), hexc(shade)))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=6 * mm, rightMargin=6 * mm, topMargin=8 * mm, bottomMargin=8 * mm,
        title='Attendance Report',
    )
    # Sums to exactly the 285mm printable width of landscape A4 (297mm less the
    # 6mm margins). Margins were trimmed from 8mm to buy the text columns another
    # 4mm: Region/Zone/Territory now carry names like "Gujranwala Zone" rather
    # than a short local code, and Photo needs no more than its 16mm thumbnail.
    widths = [
        32 * mm, 33 * mm, 35 * mm, 20 * mm, 40 * mm,
        16 * mm, 44 * mm, 17 * mm, 28 * mm, 20 * mm,
    ]
    table = Table(data, colWidths=widths[:len(COLUMNS)], repeatRows=2)
    table.setStyle(TableStyle(style))
    doc.build([table])

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

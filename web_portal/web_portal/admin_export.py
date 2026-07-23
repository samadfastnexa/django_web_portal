"""
Site-wide admin export actions (CSV + Excel).

Registered once on the custom admin site (see web_portal/admin.py), so every
model changelist gains "Export selected -> CSV / Excel" without touching each
of the ~60 ModelAdmin classes.

Column selection, in priority order:
  1. `export_fields` attribute on the ModelAdmin (list of field/callable names)
  2. the visible `list_display` (minus the selection checkbox)
  3. the model's own concrete fields
Values are resolved exactly the way the changelist resolves them, then any
HTML from badge/image callables is stripped so the cell holds plain text.
"""
import csv
import datetime
import re
from io import BytesIO

from django.contrib import admin
from django.contrib.admin.utils import label_for_field, lookup_field
from django.http import HttpResponse
from django.utils.encoding import force_str
from django.utils.html import strip_tags

_SHEET_TITLE_BAD = re.compile(r'[\[\]:*?/\\]')


def _export_columns(model_admin):
    fields = getattr(model_admin, 'export_fields', None)
    if fields:
        return list(fields)
    cols = [c for c in (model_admin.list_display or ()) if c != 'action_checkbox']
    if not cols or cols == ['__str__']:
        return [f.name for f in model_admin.model._meta.fields]
    return cols


def _header(model_admin, name):
    try:
        return force_str(label_for_field(name, model_admin.model, model_admin)).strip()
    except Exception:
        return force_str(name).replace('_', ' ').strip().title()


def _cell(model_admin, obj, name):
    try:
        _field, _attr, value = lookup_field(name, obj, model_admin)
    except Exception:
        value = getattr(obj, name, '')
        if callable(value):
            try:
                value = value()
            except Exception:
                value = ''
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    text = force_str(value)
    if '<' in text and '>' in text:          # HTML from a badge / image callable
        text = strip_tags(text)
    return text.strip()


def _rows(model_admin, queryset, columns):
    yield [_header(model_admin, c) for c in columns]
    for obj in queryset:
        yield [_cell(model_admin, obj, c) for c in columns]


def _filename(model_admin, ext):
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'{model_admin.model._meta.model_name}_export_{stamp}.{ext}'


@admin.action(description='Export selected → CSV')
def export_as_csv(model_admin, request, queryset):
    columns = _export_columns(model_admin)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="{_filename(model_admin, "csv")}"'
    )
    response.write('﻿')                 # UTF-8 BOM so Excel reads it correctly
    writer = csv.writer(response)
    for row in _rows(model_admin, queryset, columns):
        writer.writerow(row)
    return response


@admin.action(description='Export selected → Excel (.xlsx)')
def export_as_xlsx(model_admin, request, queryset):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    columns = _export_columns(model_admin)
    wb = Workbook()
    ws = wb.active
    title = _SHEET_TITLE_BAD.sub('', str(model_admin.model._meta.verbose_name_plural))
    ws.title = (title or 'Export')[:31]

    header_fill = PatternFill('solid', fgColor='E26830')
    header_font = Font(bold=True, color='FFFFFF')
    widths = {}
    for r_idx, row in enumerate(_rows(model_admin, queryset, columns), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(r_idx, c_idx, value)
            if r_idx == 1:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            widths[c_idx] = min(max(widths.get(c_idx, 10), len(value) + 2), 60)
    for c_idx, width in widths.items():
        ws.column_dimensions[get_column_letter(c_idx)].width = width
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions

    buf = BytesIO()
    wb.save(buf)
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{_filename(model_admin, "xlsx")}"'
    )
    return response

"""
Global API export.

Any DRF list endpoint responds to `?format=csv` or `?format=xlsx` with a
downloadable file containing ALL matching rows (pagination is bypassed for the
export). Wired once via DEFAULT_RENDERER_CLASSES + DEFAULT_PAGINATION_CLASS in
settings, so every endpoint gets it without per-view code.

Because content negotiation runs before the view body, the pagination class can
see the chosen format and skip paging; the renderer then receives the full list
and streams it as CSV / XLSX.
"""
import csv
import datetime
import json
from io import BytesIO, StringIO

from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import BaseRenderer

EXPORT_FORMATS = ('csv', 'xlsx')


def _extract_rows(data):
    """Normalise a DRF response body to a list of row dicts."""
    if isinstance(data, dict):
        if isinstance(data.get('results'), list):   # paginated envelope
            data = data['results']
        else:
            data = [data]
    if not isinstance(data, list):
        data = [data]
    return [item if isinstance(item, dict) else {'value': item} for item in data]


def _columns(rows):
    cols = []
    for row in rows:
        for key in row.keys():
            if key not in cols:
                cols.append(key)
    return cols


def _flatten(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _model_basename(renderer_context):
    try:
        view = renderer_context.get('view') if renderer_context else None
        model = getattr(getattr(view, 'queryset', None), 'model', None)
        if model is not None:
            return model._meta.model_name
        return getattr(view, 'basename', None) or 'export'
    except Exception:
        return 'export'


def _set_download_header(renderer_context, ext):
    if not renderer_context:
        return
    response = renderer_context.get('response')
    if response is None or 'Content-Disposition' in response:
        return
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f'{_model_basename(renderer_context)}_export_{stamp}.{ext}'
    response['Content-Disposition'] = f'attachment; filename="{name}"'


class CSVRenderer(BaseRenderer):
    media_type = 'text/csv'
    format = 'csv'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        rows = _extract_rows(data)
        cols = _columns(rows)
        buf = StringIO()
        buf.write('﻿')                     # BOM for Excel
        writer = csv.writer(buf)
        writer.writerow(cols)
        for row in rows:
            writer.writerow([_flatten(row.get(c, '')) for c in cols])
        _set_download_header(renderer_context, 'csv')
        return buf.getvalue().encode('utf-8')


class XLSXRenderer(BaseRenderer):
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    format = 'xlsx'
    render_style = 'binary'
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        rows = _extract_rows(data)
        cols = _columns(rows)
        wb = Workbook()
        ws = wb.active
        ws.title = 'Export'
        ws.append([str(c) for c in cols])
        header_fill = PatternFill('solid', fgColor='E26830')
        header_font = Font(bold=True, color='FFFFFF')
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for row in rows:
            ws.append([_flatten(row.get(c, '')) for c in cols])
        for idx, col in enumerate(cols, 1):
            sample = [len(str(col))] + [len(_flatten(r.get(col, ''))) for r in rows[:200]]
            ws.column_dimensions[get_column_letter(idx)].width = min(max(max(sample) + 2, 10), 60)
        ws.freeze_panes = 'A2'
        if ws.max_row >= 1:
            ws.auto_filter.ref = ws.dimensions
        buf = BytesIO()
        wb.save(buf)
        _set_download_header(renderer_context, 'xlsx')
        return buf.getvalue()


class ExportPageNumberPagination(PageNumberPagination):
    """
    Normal PageNumberPagination, except an export request (?format=csv|xlsx)
    disables paging so the whole result set is written to the file rather than
    just the current page. Also enables ?page_size= for JSON callers.
    """
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def paginate_queryset(self, queryset, request, view=None):
        fmt = getattr(getattr(request, 'accepted_renderer', None), 'format', None)
        if fmt in EXPORT_FORMATS:
            return None
        return super().paginate_queryset(queryset, request, view=view)

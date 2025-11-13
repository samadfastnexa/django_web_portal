Exports: XLSX and PDF Styling

Overview
- Centralized builders in `crop_manage/exports.py` generate styled Excel and page-safe PDF reports for Trials and Treatments.
- Admin actions and views now use these builders, ensuring consistent formatting and error handling across the app.

XLSX Styling
- Header: bold Calibri, contrasting background (`#bcd3e0` Trials, `#c4e7ae` Treatments), thin borders.
- Rows: readable height for headers; text wrapping enabled for wide columns in Treatments.
- Columns: sensible widths set for readability in both sheets.
- Number formats: dates (`YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`), decimals (`0.0`), integers (`0`).
- Performance: switches to write-only mode automatically for very large datasets to reduce memory usage.

PDF Styling & Pagination
- Automatic `A4` page size with margins (36pt on all sides).
- Tables use `Paragraph` for wrapping to avoid text cutoff.
- Trials and Treatments headers styled similarly to XLSX for consistency.
- Treatments are chunked into logical pages (30 rows per page) with explicit page breaks to prevent overly long single tables.

Error Handling
- If libraries are missing, builders raise a `RuntimeError` which is reported as a `500` response in views/admin.
- Large dataset handling in XLSX uses write-only mode; see limitations.

Limitations / Notes
- In write-only mode, some cell-level styles (like borders/fills on individual data rows) are not retained by openpyxl; header styling remains.
- PDF column widths are proportional to the available page width and may vary slightly depending on content.
- Very long rich text is wrapped but not truncated; overall document size will grow accordingly.

Testing
- Unit tests in `crop_manage/tests/test_exports.py` verify:
  - XLSX workbook creation, sheet names, header bold + background fill.
  - PDF generation produces a non-empty document and handles larger data volumes (page chunking scenario).

Where Used
- Admin actions: export selected/all Trials to XLSX/PDF use the builders.
- Views: endpoints for XLSX/PDF export rely on the same builders for uniform results.
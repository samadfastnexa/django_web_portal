fp = r'g:\tarzan\django_web_portal - V1\web_portal\general_ledger\views.py'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

# ── API view: replace the SAP logo block ─────────────────────────────────────
old_api_sap = """        # SAP logo drawn programmatically
        try:
            from reportlab.graphics.shapes import Drawing as _RLDrawing, Rect as _RLRect, String as _RLString
            _sap_w2, _sap_h2 = 0.55 * inch, 0.28 * inch
            _sap_d2 = _RLDrawing(_sap_w2, _sap_h2)
            _sap_d2.add(_RLRect(0, 0, _sap_w2, _sap_h2,
                                fillColor=colors.HexColor('#0070f3'),
                                strokeColor=colors.HexColor('#0070f3')))
            _sap_d2.add(_RLString(_sap_w2 / 2, (_sap_h2 / 2) - 4, 'SAP',
                                  fontSize=12, fontName='Helvetica-Bold',
                                  fillColor=colors.white, textAnchor='middle'))
            _sap_logo2 = _sap_d2
        except Exception:
            _sap_logo2 = None

        _pdate_para2 = Paragraph(f'Print Date:   {print_date_str}', _h_print)
        _sap_cell2 = _sap_logo2 if _sap_logo2 is not None else Paragraph('SAP', _h_print)"""

new_api_sap = """        # SAP logo: use uploaded image if available, else draw programmatically
        _sap_logo2 = None
        if _cfg.sap_logo_image:
            try:
                _sap_logo2 = RLImage(_cfg.sap_logo_image.path, width=0.65 * inch, height=0.33 * inch)
            except Exception:
                _sap_logo2 = None
        if _sap_logo2 is None:
            try:
                from reportlab.graphics.shapes import Drawing as _RLDrawing, Rect as _RLRect, String as _RLString
                _sap_w2, _sap_h2 = 0.55 * inch, 0.28 * inch
                _sap_d2 = _RLDrawing(_sap_w2, _sap_h2)
                _sap_d2.add(_RLRect(0, 0, _sap_w2, _sap_h2,
                                    fillColor=colors.HexColor('#0070f3'),
                                    strokeColor=colors.HexColor('#0070f3')))
                _sap_d2.add(_RLString(_sap_w2 / 2, (_sap_h2 / 2) - 4, 'SAP',
                                      fontSize=12, fontName='Helvetica-Bold',
                                      fillColor=colors.white, textAnchor='middle'))
                _sap_logo2 = _sap_d2
            except Exception:
                _sap_logo2 = None

        _pdate_para2 = Paragraph(f'Print Date:   {print_date_str}', _h_print)
        _sap_cell2 = _sap_logo2 if _sap_logo2 is not None else Paragraph('SAP', _h_print)"""

c1 = content.count(old_api_sap)
print(f'API SAP block: {c1}')
content = content.replace(old_api_sap, new_api_sap)

# ── Admin view: replace the SAP logo block ───────────────────────────────────
old_adm_sap = """        # ── SAP logo drawn programmatically (no image file required) ─────────
        try:
            from reportlab.graphics.shapes import Drawing as _RLDrawing, Rect as _RLRect, String as _RLString
            from reportlab.graphics import renderPDF as _renderPDF
            from reportlab.platypus import HRFlowable
            _sap_w, _sap_h = 0.55 * inch, 0.28 * inch
            _sap_d = _RLDrawing(_sap_w, _sap_h)
            _sap_d.add(_RLRect(0, 0, _sap_w, _sap_h,
                               fillColor=colors.HexColor('#0070f3'),
                               strokeColor=colors.HexColor('#0070f3')))
            _sap_d.add(_RLString(_sap_w / 2, (_sap_h / 2) - 4, 'SAP',
                                 fontSize=12, fontName='Helvetica-Bold',
                                 fillColor=colors.white, textAnchor='middle'))
            _sap_logo = _sap_d
        except Exception:
            _sap_logo = None

        # ── Right sub-table: [ print-date  |  SAP-logo ] ─────────────────────
        _pdate_para = Paragraph(f'Print Date:   {print_date_str}', _h_print)
        _sap_cell = _sap_logo if _sap_logo is not None else Paragraph('SAP', _h_print)"""

new_adm_sap = """        # ── SAP logo: use uploaded image if available, else draw programmatically ──
        _sap_logo = None
        if _cfg.sap_logo_image:
            try:
                _sap_logo = RLImage(_cfg.sap_logo_image.path, width=0.65 * inch, height=0.33 * inch)
            except Exception:
                _sap_logo = None
        if _sap_logo is None:
            try:
                from reportlab.graphics.shapes import Drawing as _RLDrawing, Rect as _RLRect, String as _RLString
                _sap_w, _sap_h = 0.55 * inch, 0.28 * inch
                _sap_d = _RLDrawing(_sap_w, _sap_h)
                _sap_d.add(_RLRect(0, 0, _sap_w, _sap_h,
                                   fillColor=colors.HexColor('#0070f3'),
                                   strokeColor=colors.HexColor('#0070f3')))
                _sap_d.add(_RLString(_sap_w / 2, (_sap_h / 2) - 4, 'SAP',
                                     fontSize=12, fontName='Helvetica-Bold',
                                     fillColor=colors.white, textAnchor='middle'))
                _sap_logo = _sap_d
            except Exception:
                _sap_logo = None

        # ── Right sub-table: [ print-date  |  SAP-logo ] ─────────────────────
        _pdate_para = Paragraph(f'Print Date:   {print_date_str}', _h_print)
        _sap_cell = _sap_logo if _sap_logo is not None else Paragraph('SAP', _h_print)"""

c2 = content.count(old_adm_sap)
print(f'Admin SAP block: {c2}')
content = content.replace(old_adm_sap, new_adm_sap)

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)
print('All done')

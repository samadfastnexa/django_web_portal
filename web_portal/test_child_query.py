import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.admin import get_hana_connection
from sap_integration import hana_connect

def _schema_for_company(key: str) -> str:
    try:
        from preferences.models import Setting
        s = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
        if s and isinstance(s.value, dict):
            v = s.value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        if s and isinstance(s.value, str):
            import json as _json
            try:
                data = _json.loads(s.value)
                v = data.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            except Exception:
                pass
    except Exception:
        pass
    if key == '4B-ORANG':
        return '4B-ORANG_APP'
    if key == '4B-BIO':
        return '4B-BIO_APP'
    return os.environ.get('HANA_SCHEMA') or '4B-BIO_APP'

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test child CardCode/CardName by FatherCard or FatherName')
    parser.add_argument('--father-card', dest='father_card', help='Parent CardCode (FatherCard)')
    parser.add_argument('--father-name', dest='father_name', help='Parent CardName to resolve CardCode')
    parser.add_argument('--company-db', dest='company_db', default='4B-BIO', help='Company DB key (e.g., 4B-BIO)')
    parser.add_argument('--search', dest='search', default='', help='Optional search text to filter children by CardCode or CardName')
    args = parser.parse_args()
    father_card = (args.father_card or '').strip() or 'BIC01563'
    father_name = (args.father_name or '').strip()
    company_db = (args.company_db or '4B-BIO').strip()
    db = get_hana_connection()
    if not db:
        print('Connection failed')
        return
    sch = _schema_for_company(company_db)
    cur = db.cursor()
    cur.execute(f'SET SCHEMA "{sch}"')
    cur.close()
    if not father_card and father_name:
        # Resolve father_card by exact name match first, then LIKE fallback
        cur = db.cursor()
        cur.execute(
            'SELECT T0."CardCode", T0."CardName" FROM OCRD T0 WHERE T0."CardType" = \'C\' AND T0."validFor" = \'Y\' AND UPPER(TRIM(T0."CardName")) = UPPER(TRIM(?)) ORDER BY T0."CardCode" LIMIT 1',
            (father_name,)
        )
        row = cur.fetchone()
        if not row:
            like_param = f"%{father_name}%"
            cur.execute(
                'SELECT T0."CardCode", T0."CardName" FROM OCRD T0 WHERE T0."CardType" = \'C\' AND T0."validFor" = \'Y\' AND T0."CardName" LIKE ? ORDER BY T0."CardCode" LIMIT 1',
                (like_param,)
            )
            row = cur.fetchone()
        if row:
            try:
                father_card = row[0]
                father_name = row[1]
            except Exception:
                try:
                    father_card = row.get('CardCode')
                    father_name = row.get('CardName')
                except Exception:
                    pass
        cur.close()
    rows = hana_connect.child_card_code(db, father_card, (args.search or '').strip() or None)
    db.close()
    print('FatherCard:', father_card)
    print('FatherName:', father_name)
    print('CompanyDB:', company_db, 'Schema:', sch)
    print('Count:', len(rows))
    for r in rows[:20]:
        print(str(r.get('CardCode') or ''), '-', str(r.get('CardName') or ''))

if __name__ == '__main__':
    main()

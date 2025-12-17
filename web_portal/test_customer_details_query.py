import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from FieldAdvisoryService.admin import get_hana_connection

def _load_env_file(path):
    try:
        if not os.path.exists(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                if '=' in s:
                    k, v = s.split('=', 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass

def _schema_for_company(key):
    try:
        from preferences.models import Setting
        s = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
        if s and isinstance(s.value, dict):
            v = s.value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        if s and isinstance(s.value, str):
            import json as _json
            data = _json.loads(s.value)
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    except Exception:
        pass
    if key == '4B-ORANG':
        return '4B-ORANG_APP'
    if key == '4B-BIO':
        return '4B-BIO_APP'
    return os.environ.get('HANA_SCHEMA') or '4B-BIO_APP'

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--card-code', dest='card_code', default='BIC01563')
    p.add_argument('--company-db', dest='company_db', default='4B-BIO')
    args = p.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    _load_env_file(os.path.join(here, '.env'))
    _load_env_file(os.path.join(os.getcwd(), '.env'))
    db = get_hana_connection()
    if not db:
        try:
            from hdbcli import dbapi
            db = dbapi.connect(address=os.environ.get('HANA_HOST'), port=int(os.environ.get('HANA_PORT') or '30015'), user=os.environ.get('HANA_USER') or '', password=os.environ.get('HANA_PASSWORD') or '')
        except Exception:
            db = None
    if not db:
        print('Connection failed')
        return
    sch = _schema_for_company((args.company_db or '4B-BIO').strip())
    cur = db.cursor()
    cur.execute(f'SET SCHEMA "{sch}"')
    cur.close()
    cur = db.cursor()
    cur.execute(
        'SELECT T0."CardName", T0."CntctPrsn", T0."LicTradNum", T0."BillToDef", T0."Address" FROM OCRD T0 WHERE T0."CardCode" = ?',
        (args.card_code,)
    )
    row = cur.fetchone()
    cur.close()
    db.close()
    if not row:
        print('404')
        print('{"error": "Customer not found: ' + args.card_code + '"}')
        return
    try:
        card_name = row[0]
        cntct = row[1]
        tax = row[2]
        payto = row[3]
        addr = row[4]
    except Exception:
        card_name = getattr(row, 'CardName', '')
        cntct = getattr(row, 'CntctPrsn', '')
        tax = getattr(row, 'LicTradNum', '')
        payto = getattr(row, 'BillToDef', '')
        addr = getattr(row, 'Address', '')
    import json
    print('200')
    print(json.dumps({
        'card_name': card_name,
        'contact_person_code': cntct,
        'federal_tax_id': tax,
        'pay_to_code': payto,
        'address': addr
    }))

if __name__ == '__main__':
    main()


import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

try:
    from FieldAdvisoryService.admin import get_hana_connection
except Exception:
    get_hana_connection = None

def _load_env_file(path: str):
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
    p = argparse.ArgumentParser(description='Count active customers (CardType=C, validFor=Y)')
    p.add_argument('--company-db', dest='company_db', default='4B-BIO')
    args = p.parse_args()

    # Load env
    here = os.path.dirname(os.path.abspath(__file__))
    _load_env_file(os.path.join(here, '.env'))
    _load_env_file(os.path.join(os.getcwd(), '.env'))

    # Connect
    db = None
    if callable(get_hana_connection):
        try:
            db = get_hana_connection()
        except Exception:
            db = None
    if not db:
        try:
            from hdbcli import dbapi
            host = os.environ.get('HANA_HOST')
            port = int(os.environ.get('HANA_PORT') or '30015')
            user = os.environ.get('HANA_USER') or ''
            pwd = os.environ.get('HANA_PASSWORD') or ''
            db = dbapi.connect(address=host, port=port, user=user, password=pwd)
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
    cur.execute('SELECT COUNT(*) AS C FROM OCRD WHERE "CardType" = \'C\' AND "validFor" = \'Y\'')
    r = cur.fetchone()
    cur.close()
    db.close()
    try:
        count = int(r[0]) if r else 0
    except Exception:
        count = 0
    print('CompanyDB:', args.company_db, 'Schema:', sch)
    print('Total active customers:', count)

if __name__ == '__main__':
    main()

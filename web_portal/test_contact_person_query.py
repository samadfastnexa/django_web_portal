import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from FieldAdvisoryService.admin import get_hana_connection
except Exception:
    get_hana_connection = None
from sap_integration import hana_connect

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
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ[k] = v
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
    parser = argparse.ArgumentParser(description='Test contact person queries')
    parser.add_argument('--card-code', dest='card_code')
    parser.add_argument('--contact-code', dest='contact_code')
    parser.add_argument('--company-db', dest='company_db', default='4B-BIO')
    parser.add_argument('--show-all', dest='show_all', action='store_true')
    parser.add_argument('--search', dest='search', default='')
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    _load_env_file(os.path.join(here, '.env'))
    _load_env_file(os.path.join(os.getcwd(), '.env'))
    _load_env_file(os.path.join(os.path.dirname(here), '.env'))
    _load_env_file(os.path.join(os.path.dirname(os.path.dirname(here)), '.env'))

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

    if args.show_all and not args.card_code and not args.contact_code:
        rows = hana_connect.contacts_all(db, limit=50)
        print('Mode: show_all')
        print('Count:', len(rows))
        for r in rows:
            print(str(r.get('CardCode') or ''), str(r.get('CardName') or ''), str(r.get('ContactCode') or ''), str(r.get('Name') or ''))
        db.close()
        return

    card_code = (args.card_code or '').strip()
    contact_code = (args.contact_code or '').strip()
    search = (args.search or '').strip()

    if card_code and not contact_code:
        rows = hana_connect.contacts_by_card(db, card_code, limit=100)
        if search:
            s = search.lower()
            rows = [r for r in rows if (
                (str(r.get('ContactCode') or '').lower().find(s) != -1) or
                (str(r.get('Name') or '').lower().find(s) != -1)
            )]
        print('Mode: by_card')
        print('CardCode:', card_code)
        print('Count:', len(rows))
        for r in rows:
            print(str(r.get('ContactCode') or ''), str(r.get('Name') or ''))
        db.close()
        return

    if card_code and contact_code:
        one = hana_connect.contact_person_name(db, card_code, contact_code)
        print('Mode: name_lookup')
        print('CardCode:', card_code)
        print('ContactCode:', contact_code)
        if isinstance(one, dict):
            print(str(one.get('Name') or ''))
        else:
            print(str(one or ''))
        db.close()
        return

    print('Provide --card-code to list contacts, or both --card-code and --contact-code to lookup name, or use --show-all.')
    db.close()

if __name__ == '__main__':
    main()


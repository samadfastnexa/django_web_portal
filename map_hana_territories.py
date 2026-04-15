#!/usr/bin/env python
"""
Script to map Django territories to HANA territory IDs.
This script queries HANA to find matching territory IDs and populates the hana_territory_id field.
"""
import django
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_portal'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connect import _fetch_all, _load_env_file
from FieldAdvisoryService.models import Territory, Company

_load_env_file(os.path.join(os.path.dirname(__file__), 'web_portal', 'sap_integration', '.env'))
_load_env_file(os.path.join(os.path.dirname(__file__), '.env'))

def find_hana_territories():
    """Fetch all HANA territories"""
    try:
        from hdbcli import dbapi
        cfg_host = os.environ.get('HANA_HOST') or ''
        cfg_port = os.environ.get('HANA_PORT') or '30015'
        cfg_user = os.environ.get('HANA_USER') or ''
        cfg_pwd = os.environ.get('HANA_PASSWORD') or ''
        
        kwargs = {'address': cfg_host, 'port': int(cfg_port), 'user': cfg_user, 'password': cfg_pwd}
        conn = dbapi.connect(**kwargs)
        
        # Set schema
        cur = conn.cursor()
        cur.execute('SET SCHEMA "4B-AGRI_LIVE"')
        cur.close()
        
        # Get all HANA territories
        sql = "SELECT \"territryID\", \"descript\" FROM OTER ORDER BY \"territryID\""
        hana_territories = _fetch_all(conn, sql)
        conn.close()
        return hana_territories
    except Exception as e:
        print(f"Error fetching HANA territories: {e}")
        return []

def find_best_match(django_name, hana_territories):
    """Find the best matching HANA territory for a Django territory"""
    django_upper = django_name.upper()
    
    # Try exact match first
    for ht in hana_territories:
        if ht['descript'].upper() == django_upper:
            return ht
    
    # Try partial matches - look for Territory (not Pocket)
    best_matches = []
    for ht in hana_territories:
        desc_upper = ht['descript'].upper()
        if 'TERRITORY' in desc_upper and django_upper in desc_upper:
            best_matches.append(ht)
    
    if best_matches:
        # Prefer the one that's exactly "Territory" (not modified like "xKhuzdar Territory")
        for m in best_matches:
            if m['descript'].upper() == f"{django_upper} TERRITORY":
                return m
        return best_matches[0]
    
    # Try without case sensitivity
    for ht in hana_territories:
        if django_upper in ht['descript'].upper():
            return ht
    
    return None

def map_territories_for_company(company_schema_name):
    """Map territories for a specific company"""
    print(f"\n=== Mapping territories for company: {company_schema_name} ===")
    
    # Get HANA territories
    print("Fetching HANA territories...")
    hana_territories = find_hana_territories()
    if not hana_territories:
        print("❌ No HANA territories found!")
        return
    
    print(f"✅ Found {len(hana_territories)} HANA territories")
    
    # Get Django territories for this company
    try:
        company = Company.objects.get(name=company_schema_name)
    except Company.DoesNotExist:
        print(f"❌ Company {company_schema_name} not found in Django!")
        return
    
    territories = Territory.objects.filter(company=company)
    print(f"✅ Found {len(territories)} Django territories for {company_schema_name}")
    
    mapped = 0
    unmapped = 0
    
    for t in territories:
        match = find_best_match(t.name, hana_territories)
        if match:
            if t.hana_territory_id != match['territryID']:
                t.hana_territory_id = match['territryID']
                t.save()
                print(f"  ✅ {t.name:30} -> HANA ID {match['territryID']:4} ({match['descript']})")
                mapped += 1
            else:
                print(f"  ℹ️  {t.name:30} -> Already mapped to HANA ID {t.hana_territory_id}")
                mapped += 1
        else:
            print(f"  ❌ {t.name:30} -> NO MATCH FOUND in HANA")
            unmapped += 1
    
    print(f"\n📊 Summary: {mapped} mapped, {unmapped} unmapped")
    return mapped, unmapped

if __name__ == '__main__':
    # Map territories for 4B-AGRI_LIVE
    try:
        map_territories_for_company('4B-AGRI_LIVE')
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

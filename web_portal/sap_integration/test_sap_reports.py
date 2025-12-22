import os
import sys
import json
import argparse
from datetime import datetime

# Add current directory to path to import hana_connect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import hana_connect

def setup_env():
    """Load environment variables."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(project_root, '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(os.path.dirname(hana_connect.__file__), '.env')
    
    print(f"Loading env from: {env_path}")
    hana_connect._load_env_file(env_path)

def get_db_connection():
    """Establish HANA database connection."""
    host = os.environ.get('HANA_HOST')
    port = os.environ.get('HANA_PORT', '30015')
    user = os.environ.get('HANA_USER')
    password = os.environ.get('HANA_PASSWORD')
    
    if not host or not user or not password:
        print("Missing HANA credentials in .env")
        sys.exit(1)
        
    print(f"Connecting to {host}:{port} as {user}...")
    try:
        db = hana_connect._connect_hdbcli(host, port, user, password, None, None, None)
        print("Connected successfully.")
        return db
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

def print_swagger_info(report_name, params):
    """
    Simulate Swagger/OpenAPI documentation for the report.
    """
    print("\n" + "="*50)
    print(f"REPORT: {report_name}")
    print("="*50)
    print("DESCRIPTION:")
    if report_name == 'sales_vs_achievement_geo_inv':
        print("  Sales vs Achievement based on Geo Location (Invoices).")
        print("  Hierarchy: Region -> Zone -> Territory")
        print("  Source: B4_COLLECTION_TARGET, OTER, B4_EMP, OHEM")
    elif report_name == 'sales_vs_achievement_geo_profit':
        print("  Sales vs Achievement based on Geo Location (Gross Profit).")
        print("  Hierarchy: Region -> Zone -> Territory")
        print("  Source: OINV, OCRD, OTER, OSLP")
    elif report_name == 'geo_options':
        print("  Geo Options (Regions, Zones, Territories).")
        print("  Source: OTER")
    
    print("\nPARAMETERS (Filters):")
    for p, v in params.items():
        print(f"  - {p}: {v} ({type(v).__name__})")
    print("-" * 50 + "\n")

def test_report(db, report_name, func, **kwargs):
    """
    Generic test function for a report.
    """
    print_swagger_info(report_name, kwargs)
    
    start_time = datetime.now()
    try:
        # Set Schema to 4B-BIO_APP as these tables reside there
        db.cursor().execute("SET SCHEMA \"4B-BIO_APP\"")
        
        results = func(db, **kwargs)
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\nSTATUS: Success")
        print(f"DURATION: {duration:.4f} seconds")
        
        if isinstance(results, list):
            print(f"ROW COUNT: {len(results)}")
            if len(results) > 0:
                print(f"\nSAMPLE DATA (First 3 rows):")
                for i, row in enumerate(results[:3]):
                    print(f"  Row {i+1}: {row}")
            else:
                print("\nNO DATA FOUND with current filters.")
        else:
            print(f"RESULT: {results}")
            
    except Exception as e:
        print(f"\nSTATUS: FAILED")
        print(f"ERROR: {e}")
    
    print("\n" + "="*50 + "\n")

if __name__ == '__main__':
    setup_env()
    db = get_db_connection()
    
    print("\nStarting SAP Reports Test Suite...")
    print(f"Time: {datetime.now()}")
    
    # Test Geo Options
    print(">>> TEST CASE 0: Geo Options")
    test_report(db, 'geo_options', hana_connect.geo_options)

    # --- Test Case 1: Geo Inv - All Data ---
    print("\n>>> TEST CASE 1: Geo Inv (No Filters)")
    test_report(db, 'sales_vs_achievement_geo_inv', hana_connect.sales_vs_achievement_geo_inv)
    
    # --- Test Case 2: Geo Inv - With Filters ---
    print("\n>>> TEST CASE 2: Geo Inv (With Region Filter)")
    # Note: Replace 'Lahore' with a valid region from your DB if known, or leave generic
    test_report(db, 'sales_vs_achievement_geo_inv', hana_connect.sales_vs_achievement_geo_inv, region='Lahore')

    # --- Test Case 3: Geo Inv - With Emp ID ---
    print("\n>>> TEST CASE 3: Geo Inv (With Emp ID)")
    # Replace 1 with valid emp ID
    test_report(db, 'sales_vs_achievement_geo_inv', hana_connect.sales_vs_achievement_geo_inv, emp_id=1)

    # --- Test Case 4: Geo Profit - All Data ---
    print("\n>>> TEST CASE 4: Geo Profit (No Filters)")
    test_report(db, 'sales_vs_achievement_geo_profit', hana_connect.sales_vs_achievement_geo_profit)

    # --- Test Case 5: Geo Profit - Date Range ---
    print("\n>>> TEST CASE 5: Geo Profit (Date Range)")
    test_report(db, 'sales_vs_achievement_geo_profit', hana_connect.sales_vs_achievement_geo_profit, start_date='2023-01-01', end_date='2023-12-31')

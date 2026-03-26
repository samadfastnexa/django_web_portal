#!/usr/bin/env python3
"""
Simple B4_SALES_TARGET Diagnostic using existing HANA connection method
======================================================================
"""

import os
import sys
from dotenv import load_dotenv

# Add Django project path to import SAP integration
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_portal'))

def main():
    """Main diagnostic function using existing codebase connection method"""

    # Load environment variables
    load_dotenv()

    print("B4_SALES_TARGET Simple Diagnostic Tool")
    print("Using existing codebase connection method")
    print("="*60)

    # Import from the existing codebase
    try:
        from sap_integration import hana_connect
        print("SUCCESS: Imported sap_integration.hana_connect")
    except ImportError as e:
        print(f"ERROR: Cannot import sap_integration module: {e}")
        return

    # Get connection details
    host = os.environ.get('HANA_HOST')
    port = os.environ.get('HANA_PORT', '30015')
    user = os.environ.get('HANA_USER')
    password = os.environ.get('HANA_PASSWORD')
    schema = os.environ.get('HANA_SCHEMA', '4B-AGRI_LIVE')

    print(f"\nConnection Details:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  User: {user}")
    print(f"  Schema: {schema}")

    if not host or not user or not password:
        print("ERROR: Missing HANA credentials in .env file")
        return

    # Connect using the same method as test_sap_reports.py
    try:
        print(f"\nConnecting to {host}:{port} as {user}...")
        db = hana_connect._connect_hdbcli(host, port, user, password, None, None, None)
        print("SUCCESS: Connected to HANA database")
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        return

    # Test basic query
    try:
        print("\nTesting basic query...")
        cursor = db.cursor()
        cursor.execute("SELECT CURRENT_UTCTIMESTAMP AS TS FROM DUMMY")
        result = cursor.fetchone()
        print(f"SUCCESS: Basic query result: {result}")
        cursor.close()
    except Exception as e:
        print(f"ERROR: Basic query failed: {e}")
        db.close()
        return

    # Check for B4_SALES_TARGET table
    print(f"\n" + "="*60)
    print("CHECKING B4_SALES_TARGET TABLE")
    print("="*60)

    try:
        cursor = db.cursor()

        # Query to find B4_SALES_TARGET across all schemas
        query = """
        SELECT
            SCHEMA_NAME,
            TABLE_NAME,
            TABLE_TYPE
        FROM TABLES
        WHERE TABLE_NAME = 'B4_SALES_TARGET'
        ORDER BY SCHEMA_NAME
        """

        cursor.execute(query)
        results = cursor.fetchall()

        if results:
            print(f"SUCCESS: Found {len(results)} B4_SALES_TARGET table(s):")
            for row in results:
                schema_name, table_name, table_type = row
                print(f"  Schema: {schema_name}")
                print(f"  Table: {table_name} ({table_type})")
                print()

                # Get record count separately
                try:
                    count_query = f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"'
                    cursor.execute(count_query)
                    count_result = cursor.fetchone()
                    record_count = count_result[0] if count_result else 0
                    print(f"  Records: {record_count}")
                except Exception as e:
                    print(f"  Records: Unable to count ({e})")
                print()
        else:
            print("WARNING: B4_SALES_TARGET table NOT FOUND in any schema!")
            print("\nLet's check for similar sales/target tables...")

            # Check for similar tables
            similar_query = """
            SELECT SCHEMA_NAME, TABLE_NAME
            FROM TABLES
            WHERE (TABLE_NAME LIKE '%SALES%' OR TABLE_NAME LIKE '%TARGET%')
            AND SCHEMA_NAME IN ('4B-AGRI_LIVE', '4B-ORANG_LIVE', 'FOURB', '4B-BIO_APP', '4B-ORANG_APP')
            ORDER BY SCHEMA_NAME, TABLE_NAME
            """

            cursor.execute(similar_query)
            similar_results = cursor.fetchall()

            if similar_results:
                print(f"\nFound {len(similar_results)} sales/target-related tables:")
                for row in similar_results:
                    schema_name, table_name = row
                    print(f"  {schema_name}.{table_name}")
            else:
                print("\nNo sales/target-related tables found in target schemas")

        cursor.close()

    except Exception as e:
        print(f"ERROR: Table check failed: {e}")
    finally:
        db.close()
        print(f"\nConnection closed.")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if 'results' in locals() and results:
        print("RESULT: B4_SALES_TARGET table exists in your local HANA database")
        print("RECOMMENDATION: The server issue is likely due to:")
        print("  1. Missing table synchronization between local and server")
        print("  2. Different schema names between environments")
        print("  3. Different SAP database versions")
        print("NEXT STEP: Check if the server HANA database has this table")
    else:
        print("RESULT: B4_SALES_TARGET table does NOT exist in your local HANA")
        print("RECOMMENDATION: This explains the server error")
        print("NEXT STEPS:")
        print("  1. Check if table should exist in SAP B1")
        print("  2. Verify table name spelling")
        print("  3. Check if it's in a different schema")

if __name__ == "__main__":
    main()
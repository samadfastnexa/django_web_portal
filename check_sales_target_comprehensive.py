#!/usr/bin/env python3
"""
Comprehensive B4_SALES_TARGET Table Diagnostic Script
====================================================
This script checks for the B4_SALES_TARGET table across all schemas in your SAP HANA database
and provides detailed information about table structure and data availability.
"""

import os
import sys
import pyodbc
from datetime import datetime

def get_hana_connection():
    """Get HANA database connection using environment variables"""
    try:
        hana_server = os.environ.get('HANA_SERVER', '192.168.1.19')
        hana_port = os.environ.get('HANA_PORT', '30013')
        hana_user = os.environ.get('HANA_USER', 'FOURB')
        hana_password = os.environ.get('HANA_PASSWORD', 'Fourb@2023')

        connection_string = (
            f'DRIVER={{HDBODBC}};'
            f'SERVERNODE={hana_server}:{hana_port};'
            f'UID={hana_user};'
            f'PWD={hana_password};'
        )

        conn = pyodbc.connect(connection_string)
        print(f"✅ Connected to HANA server: {hana_server}:{hana_port}")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to HANA: {e}")
        return None

def check_table_existence(cursor):
    """Check for B4_SALES_TARGET table across all schemas"""
    print("\n" + "="*60)
    print("🔍 CHECKING B4_SALES_TARGET TABLE EXISTENCE")
    print("="*60)

    # Query to find B4_SALES_TARGET in any schema
    query = """
    SELECT
        SCHEMA_NAME,
        TABLE_NAME,
        TABLE_TYPE,
        CREATE_TIME,
        RECORD_COUNT
    FROM TABLES
    WHERE TABLE_NAME = 'B4_SALES_TARGET'
    ORDER BY SCHEMA_NAME
    """

    try:
        cursor.execute(query)
        results = cursor.fetchall()

        if results:
            print(f"📊 Found {len(results)} B4_SALES_TARGET table(s):")
            for row in results:
                schema, table, table_type, create_time, record_count = row
                print(f"   📍 Schema: {schema}")
                print(f"      Table: {table}")
                print(f"      Type: {table_type}")
                print(f"      Created: {create_time}")
                print(f"      Records: {record_count}")
                print()
            return results
        else:
            print("❌ B4_SALES_TARGET table NOT FOUND in any schema!")
            return []
    except Exception as e:
        print(f"❌ Error checking table existence: {e}")
        return []

def check_schema_tables(cursor, schema_name):
    """Check what tables exist in a specific schema"""
    print(f"\n🔍 TABLES IN SCHEMA '{schema_name}':")
    print("-" * 40)

    query = """
    SELECT
        TABLE_NAME,
        TABLE_TYPE,
        RECORD_COUNT
    FROM TABLES
    WHERE SCHEMA_NAME = ?
    AND TABLE_NAME LIKE '%SALES%'
    ORDER BY TABLE_NAME
    """

    try:
        cursor.execute(query, (schema_name,))
        results = cursor.fetchall()

        if results:
            print(f"📋 Found {len(results)} sales-related tables:")
            for row in results:
                table_name, table_type, record_count = row
                print(f"   📊 {table_name} ({table_type}) - {record_count} records")
        else:
            print(f"❌ No sales-related tables found in {schema_name}")

        return results
    except Exception as e:
        print(f"❌ Error checking schema tables: {e}")
        return []

def analyze_table_structure(cursor, schema_name, table_name):
    """Get detailed structure of B4_SALES_TARGET table if it exists"""
    print(f"\n📋 ANALYZING TABLE STRUCTURE: {schema_name}.{table_name}")
    print("-" * 50)

    # Get column information
    query = """
    SELECT
        COLUMN_NAME,
        DATA_TYPE_NAME,
        LENGTH,
        IS_NULLABLE,
        DEFAULT_VALUE
    FROM TABLE_COLUMNS
    WHERE SCHEMA_NAME = ? AND TABLE_NAME = ?
    ORDER BY POSITION
    """

    try:
        cursor.execute(query, (schema_name, table_name))
        columns = cursor.fetchall()

        if columns:
            print("🏛️  Column Structure:")
            for col in columns:
                col_name, data_type, length, nullable, default = col
                nullable_str = "NULL" if nullable == "TRUE" else "NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""
                print(f"   📄 {col_name}: {data_type}({length}) {nullable_str}{default_str}")

            return True
        else:
            print("❌ No column information found")
            return False
    except Exception as e:
        print(f"❌ Error analyzing table structure: {e}")
        return False

def check_sample_data(cursor, schema_name, table_name):
    """Get sample data from the table"""
    print(f"\n📊 SAMPLE DATA FROM {schema_name}.{table_name}:")
    print("-" * 40)

    query = f"SELECT TOP 5 * FROM \"{schema_name}\".\"{table_name}\""

    try:
        cursor.execute(query)
        results = cursor.fetchall()

        if results:
            print(f"📋 Sample records (showing first 5):")
            for i, row in enumerate(results, 1):
                print(f"   Record {i}: {dict(zip([col[0] for col in cursor.description], row))}")
        else:
            print("📭 Table exists but contains no data")

        return len(results) > 0
    except Exception as e:
        print(f"❌ Error retrieving sample data: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🔬 B4_SALES_TARGET Comprehensive Diagnostic Tool")
    print(f"⏰ Started at: {datetime.now()}")
    print("="*60)

    # Get database connection
    conn = get_hana_connection()
    if not conn:
        return

    cursor = conn.cursor()

    try:
        # 1. Check if B4_SALES_TARGET exists anywhere
        found_tables = check_table_existence(cursor)

        # 2. Check specific schemas for sales-related tables
        target_schemas = ['4B-AGRI_LIVE', '4B-ORANG_LIVE', 'FOURB', '4B-BIO_APP', '4B-ORANG_APP']

        print("\n" + "="*60)
        print("🔍 CHECKING TARGET SCHEMAS")
        print("="*60)

        for schema in target_schemas:
            check_schema_tables(cursor, schema)

        # 3. Analyze table structure and data if found
        if found_tables:
            for table_info in found_tables:
                schema_name = table_info[0]
                table_name = table_info[1]

                print("\n" + "="*60)
                print(f"📊 DETAILED ANALYSIS: {schema_name}.{table_name}")
                print("="*60)

                if analyze_table_structure(cursor, schema_name, table_name):
                    check_sample_data(cursor, schema_name, table_name)

        # 4. Summary and recommendations
        print("\n" + "="*60)
        print("📋 SUMMARY AND RECOMMENDATIONS")
        print("="*60)

        if found_tables:
            print("✅ B4_SALES_TARGET table found in the following schemas:")
            for table_info in found_tables:
                print(f"   📍 {table_info[0]} (Records: {table_info[4]})")
            print("\n💡 Recommendations:")
            print("   1. Verify which schema your application is using")
            print("   2. Check if the server database has the same table in the same schema")
            print("   3. Consider data synchronization if schemas differ")
        else:
            print("❌ B4_SALES_TARGET table not found in any schema!")
            print("\n💡 Recommendations:")
            print("   1. Check if the table name is correct")
            print("   2. Verify if it exists in a different schema")
            print("   3. Check if it needs to be created/imported")
            print("   4. Review SAP B1 database structure")

    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
    finally:
        cursor.close()
        conn.close()
        print(f"\n⏰ Completed at: {datetime.now()}")

if __name__ == "__main__":
    main()
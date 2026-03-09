"""
Check OPRJ (Projects) table structure and data from SAP HANA
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.hana_connection import get_hana_connection

def check_oprj_structure():
    """Check the structure of OPRJ table"""
    print("\n=== OPRJ TABLE STRUCTURE ===")
    
    db = get_hana_connection()
    cursor = db.cursor()
    
    try:
        # Get column information
        query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE_NAME,
            LENGTH,
            IS_NULLABLE,
            COMMENTS
        FROM SYS.TABLE_COLUMNS
        WHERE SCHEMA_NAME = (SELECT TOP 1 SCHEMA_NAME FROM SYS.SCHEMAS WHERE SCHEMA_NAME LIKE '%4B%' ORDER BY SCHEMA_NAME)
        AND TABLE_NAME = 'OPRJ'
        ORDER BY POSITION
        """
        
        cursor.execute(query)
        columns = cursor.fetchall()
        
        if columns:
            print(f"\nFound {len(columns)} columns in OPRJ table:\n")
            print(f"{'Column Name':<30} {'Type':<20} {'Length':<10} {'Nullable':<10} {'Comments'}")
            print("-" * 100)
            
            for col in columns:
                col_name = col[0]
                data_type = col[1]
                length = col[2] if col[2] else ''
                nullable = col[3]
                comments = col[4] if col[4] else ''
                print(f"{col_name:<30} {data_type:<20} {str(length):<10} {nullable:<10} {comments}")
        else:
            print("No columns found. Trying alternative method...")
            
    except Exception as e:
        print(f"Error getting structure: {e}")
        print("\nTrying to get sample data instead...")
    finally:
        cursor.close()


def check_oprj_data():
    """Check sample data from OPRJ table"""
    print("\n\n=== OPRJ TABLE SAMPLE DATA ===")
    
    db = get_hana_connection()
    cursor = db.cursor()
    
    try:
        # Get first 5 records with all columns
        query = """
        SELECT TOP 5 *
        FROM "OPRJ"
        ORDER BY "PrjCode"
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Get column names from cursor description
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            print(f"\nColumns ({len(columns)}):")
            print(", ".join(columns))
            print("\n" + "=" * 120)
            
            print(f"\nSample Records ({len(rows)} records):\n")
            for i, row in enumerate(rows, 1):
                print(f"Record {i}:")
                for col_name, value in zip(columns, row):
                    print(f"  {col_name}: {value}")
                print()
        else:
            print("No data found")
            
    except Exception as e:
        print(f"Error getting data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        db.close()


def check_oprj_count():
    """Check total count of records"""
    print("\n=== OPRJ TABLE STATISTICS ===")
    
    db = get_hana_connection()
    cursor = db.cursor()
    
    try:
        # Total count
        query = 'SELECT COUNT(*) FROM "OPRJ"'
        cursor.execute(query)
        total = cursor.fetchone()[0]
        print(f"Total Projects: {total}")
        
        # Active count
        query = 'SELECT COUNT(*) FROM "OPRJ" WHERE "Active" = \'Y\''
        cursor.execute(query)
        active = cursor.fetchone()[0]
        print(f"Active Projects: {active}")
        
        # Projects with U_pol
        query = 'SELECT COUNT(*) FROM "OPRJ" WHERE "U_pol" IS NOT NULL AND "U_pol" <> \'\''
        cursor.execute(query)
        with_policy = cursor.fetchone()[0]
        print(f"Projects with Policy (U_pol): {with_policy}")
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
    finally:
        cursor.close()
        db.close()


if __name__ == '__main__':
    print("=" * 120)
    print("OPRJ (SAP PROJECTS) TABLE INSPECTION")
    print("=" * 120)
    
    try:
        check_oprj_count()
        check_oprj_structure()
        check_oprj_data()
        
        print("\n" + "=" * 120)
        print("INSPECTION COMPLETE")
        print("=" * 120)
        
    except Exception as e:
        print(f"\nFailed to connect or query: {e}")
        import traceback
        traceback.print_exc()

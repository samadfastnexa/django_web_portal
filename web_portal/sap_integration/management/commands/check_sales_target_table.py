"""
Django Management Command: Check B4_SALES_TARGET Table
=====================================================
Usage: PYTHONUTF8=1 python manage.py check_sales_target_table
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import pyodbc
from datetime import datetime


class Command(BaseCommand):
    help = 'Check B4_SALES_TARGET table existence across SAP HANA schemas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            help='Specific schema to check (default: check all schemas)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔬 B4_SALES_TARGET Diagnostic Tool'))
        self.stdout.write(f"⏰ Started at: {datetime.now()}")
        self.stdout.write("=" * 60)

        # Get database connection
        conn = self.get_hana_connection()
        if not conn:
            return

        cursor = conn.cursor()

        try:
            if options['schema']:
                # Check specific schema
                self.check_specific_schema(cursor, options['schema'], options['verbose'])
            else:
                # Check all schemas
                self.check_all_schemas(cursor, options['verbose'])

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Diagnostic failed: {e}"))
        finally:
            cursor.close()
            conn.close()
            self.stdout.write(f"\n⏰ Completed at: {datetime.now()}")

    def get_hana_connection(self):
        """Get HANA database connection"""
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
            self.stdout.write(self.style.SUCCESS(f"✅ Connected to HANA server: {hana_server}:{hana_port}"))
            return conn
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to connect to HANA: {e}"))
            return None

    def check_all_schemas(self, cursor, verbose=False):
        """Check B4_SALES_TARGET across all schemas"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🔍 CHECKING B4_SALES_TARGET TABLE EXISTENCE")
        self.stdout.write("=" * 60)

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
                self.stdout.write(self.style.SUCCESS(f"📊 Found {len(results)} B4_SALES_TARGET table(s):"))
                for row in results:
                    schema, table, table_type, create_time, record_count = row
                    self.stdout.write(f"   📍 Schema: {schema}")
                    self.stdout.write(f"      Table: {table}")
                    self.stdout.write(f"      Type: {table_type}")
                    self.stdout.write(f"      Created: {create_time}")
                    self.stdout.write(f"      Records: {record_count}")
                    self.stdout.write("")

                    if verbose:
                        self.analyze_table_details(cursor, schema, table)

                return results
            else:
                self.stdout.write(self.style.ERROR("❌ B4_SALES_TARGET table NOT FOUND in any schema!"))
                # Check for similar tables
                self.check_similar_tables(cursor)
                return []

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error checking table existence: {e}"))
            return []

    def check_specific_schema(self, cursor, schema_name, verbose=False):
        """Check B4_SALES_TARGET in a specific schema"""
        self.stdout.write(f"\n🔍 CHECKING SCHEMA: {schema_name}")
        self.stdout.write("-" * 40)

        # Check if the schema exists
        schema_query = "SELECT SCHEMA_NAME FROM M_DATABASES WHERE SCHEMA_NAME = ?"
        try:
            cursor.execute(schema_query, (schema_name,))
            if not cursor.fetchone():
                self.stdout.write(self.style.ERROR(f"❌ Schema '{schema_name}' does not exist!"))
                return

            # Check for B4_SALES_TARGET in the specific schema
            query = """
            SELECT
                TABLE_NAME,
                TABLE_TYPE,
                CREATE_TIME,
                RECORD_COUNT
            FROM TABLES
            WHERE SCHEMA_NAME = ? AND TABLE_NAME = 'B4_SALES_TARGET'
            """

            cursor.execute(query, (schema_name,))
            result = cursor.fetchone()

            if result:
                table_name, table_type, create_time, record_count = result
                self.stdout.write(self.style.SUCCESS(f"✅ Found B4_SALES_TARGET in {schema_name}:"))
                self.stdout.write(f"   📊 Type: {table_type}")
                self.stdout.write(f"   📅 Created: {create_time}")
                self.stdout.write(f"   📋 Records: {record_count}")

                if verbose:
                    self.analyze_table_details(cursor, schema_name, 'B4_SALES_TARGET')
            else:
                self.stdout.write(self.style.ERROR(f"❌ B4_SALES_TARGET not found in {schema_name}"))
                # Show sales-related tables in this schema
                self.show_sales_tables_in_schema(cursor, schema_name)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error checking schema {schema_name}: {e}"))

    def check_similar_tables(self, cursor):
        """Check for tables with similar names"""
        self.stdout.write("\n🔍 Looking for similar table names...")

        query = """
        SELECT SCHEMA_NAME, TABLE_NAME, RECORD_COUNT
        FROM TABLES
        WHERE TABLE_NAME LIKE '%SALES%' OR TABLE_NAME LIKE '%TARGET%'
        ORDER BY SCHEMA_NAME, TABLE_NAME
        """

        try:
            cursor.execute(query)
            results = cursor.fetchall()

            if results:
                self.stdout.write(f"📋 Found {len(results)} sales/target-related tables:")
                for row in results:
                    schema, table, record_count = row
                    self.stdout.write(f"   📊 {schema}.{table} ({record_count} records)")
            else:
                self.stdout.write("❌ No similar tables found")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error checking similar tables: {e}"))

    def show_sales_tables_in_schema(self, cursor, schema_name):
        """Show sales-related tables in a specific schema"""
        query = """
        SELECT TABLE_NAME, TABLE_TYPE, RECORD_COUNT
        FROM TABLES
        WHERE SCHEMA_NAME = ? AND (TABLE_NAME LIKE '%SALES%' OR TABLE_NAME LIKE '%TARGET%')
        ORDER BY TABLE_NAME
        """

        try:
            cursor.execute(query, (schema_name,))
            results = cursor.fetchall()

            if results:
                self.stdout.write(f"📋 Sales/target-related tables in {schema_name}:")
                for row in results:
                    table_name, table_type, record_count = row
                    self.stdout.write(f"   📊 {table_name} ({table_type}) - {record_count} records")
            else:
                self.stdout.write(f"📭 No sales/target-related tables in {schema_name}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error checking tables in {schema_name}: {e}"))

    def analyze_table_details(self, cursor, schema_name, table_name):
        """Get detailed information about the table"""
        self.stdout.write(f"\n📋 ANALYZING {schema_name}.{table_name}:")

        # Get column structure
        query = """
        SELECT
            COLUMN_NAME,
            DATA_TYPE_NAME,
            LENGTH,
            IS_NULLABLE
        FROM TABLE_COLUMNS
        WHERE SCHEMA_NAME = ? AND TABLE_NAME = ?
        ORDER BY POSITION
        """

        try:
            cursor.execute(query, (schema_name, table_name))
            columns = cursor.fetchall()

            if columns:
                self.stdout.write("   🏛️  Columns:")
                for col in columns:
                    col_name, data_type, length, nullable = col
                    nullable_str = "NULL" if nullable == "TRUE" else "NOT NULL"
                    self.stdout.write(f"      {col_name}: {data_type}({length}) {nullable_str}")

                # Get sample data
                sample_query = f'SELECT TOP 3 * FROM "{schema_name}"."{table_name}"'
                cursor.execute(sample_query)
                sample_data = cursor.fetchall()

                if sample_data:
                    self.stdout.write("   📊 Sample data:")
                    col_names = [col[0] for col in cursor.description]
                    for i, row in enumerate(sample_data, 1):
                        self.stdout.write(f"      Row {i}: {dict(zip(col_names, row))}")
                else:
                    self.stdout.write("   📭 Table exists but contains no data")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error analyzing table details: {e}"))
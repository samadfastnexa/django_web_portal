"""
Management command to test collection vs achievement report with logging
"""

import logging
import os
import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from decouple import config

logger = logging.getLogger('hana')


class Command(BaseCommand):
    help = 'Test collection vs achievement report and display output to console'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-db',
            type=str,
            default='4B-BIO',
            help='Database key (4B-BIO, 4B-ORANG, etc.)',
        )
        parser.add_argument(
            '--region',
            type=str,
            default=None,
            help='Filter by region name',
        )
        parser.add_argument(
            '--zone',
            type=str,
            default=None,
            help='Filter by zone name',
        )
        parser.add_argument(
            '--territory',
            type=str,
            default=None,
            help='Filter by territory name',
        )

    def handle(self, *args, **options):
        # Load .env from parent directory if it exists
        env_paths = [
            Path(settings.BASE_DIR).parent / '.env',
            Path(settings.BASE_DIR) / '.env',
            Path.cwd() / '.env',
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                self.stdout.write(self.style.SUCCESS(f'Loading .env from: {env_path}'))
                from dotenv import load_dotenv
                load_dotenv(env_path)
                break
        
        from sap_integration.hana_connect import collection_vs_achievement
        
        company_db = options.get('company_db', '4B-BIO')
        region = options.get('region')
        zone = options.get('zone')
        territory = options.get('territory')
        
        self.stdout.write(self.style.SUCCESS(f'Testing Collection VS Achievement Report'))
        self.stdout.write(self.style.WARNING(f'Database: {company_db}'))
        self.stdout.write(self.style.WARNING(f'Region: {region}, Zone: {zone}, Territory: {territory}'))
        
        try:
            # Get HANA connection - following the same pattern as hana_connect_admin
            try:
                from hdbcli import dbapi
                self.stdout.write(self.style.SUCCESS('hdbcli imported successfully'))
            except ImportError as e:
                self.stdout.write(self.style.ERROR(f'Failed to import hdbcli: {e}'))
                return
            
            # Load HANA configuration from environment using decouple
            host = config('HANA_HOST', default=None)
            port = config('HANA_PORT', cast=int, default=30015)
            user = config('HANA_USER', default=None)
            password = config('HANA_PASSWORD', default=None)
            schema = config('HANA_SCHEMA', default='4B-BIO_APP')
            
            self.stdout.write(self.style.WARNING(f'Host: {host}, Port: {port}, User: {user}, Schema: {schema}'))
            
            if not host:
                self.stdout.write(self.style.ERROR('Missing HANA_HOST environment variable'))
                return
            
            # Create connection
            kwargs = {
                'address': host,
                'port': port,
                'user': user or '',
                'password': password or ''
            }
            
            self.stdout.write(self.style.WARNING('Connecting to HANA...'))
            conn = dbapi.connect(**kwargs)
            self.stdout.write(self.style.SUCCESS('Connected to HANA successfully'))
            
            # Set schema
            cur = conn.cursor()
            cur.execute(f'SET SCHEMA "{schema}"')
            cur.close()
            self.stdout.write(self.style.SUCCESS(f'Schema set to {schema}'))
            
            # Call collection_vs_achievement function
            self.stdout.write(self.style.WARNING('Calling collection_vs_achievement function...'))
            logger.info(f'Starting collection vs achievement report for {company_db}')
            
            data = collection_vs_achievement(
                conn,
                region=region,
                zone=zone,
                territory=territory,
                ignore_emp_filter=True
            )
            
            self.stdout.write(self.style.SUCCESS(f'Report generated successfully'))
            self.stdout.write(self.style.SUCCESS(f'Total rows returned: {len(data) if data else 0}'))
            
            if data:
                self.stdout.write(self.style.SUCCESS('\nFirst row data:'))
                for k, v in list(data[0].items())[:5]:
                    self.stdout.write(f'  {k}: {v}')
            
            conn.close()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            logger.exception('Error in collection vs achievement report')

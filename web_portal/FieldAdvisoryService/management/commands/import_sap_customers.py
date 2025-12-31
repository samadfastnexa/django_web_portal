"""
Django management command to import customers from SAP HANA to Dealer model
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from hdbcli import dbapi
import os
from dotenv import load_dotenv

load_dotenv()


class Command(BaseCommand):
    help = 'Import customers from SAP HANA OCRD table to Django Dealer model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving to database',
        )
        parser.add_argument(
            '--schema',
            type=str,
            help='Specific schema to import (4B-BIO_APP or 4B-ORANG_APP)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of records to import (for testing)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_schema = options.get('schema')
        limit = options.get('limit')
        
        conn = dbapi.connect(
            address=os.getenv('HANA_HOST'),
            port=int(os.getenv('HANA_PORT')),
            user=os.getenv('HANA_USER'),
            password=os.getenv('HANA_PASSWORD')
        )

        # Map schemas to companies
        schema_company_map = {
            '4B-BIO_APP': '4B-BIO',
            '4B-ORANG_APP': '4B-ORANG'
        }
        
        schemas = [specific_schema] if specific_schema else ['4B-BIO_APP', '4B-ORANG_APP']
        
        total_processed = 0
        total_created = 0
        total_updated = 0
        total_skipped = 0

        for schema in schemas:
            if schema not in schema_company_map:
                self.stdout.write(self.style.WARNING(f"Unknown schema: {schema}"))
                continue
                
            company_key = schema_company_map[schema]
            
            self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
            self.stdout.write(self.style.SUCCESS(f"Processing Schema: {schema} (Company: {company_key})"))
            self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))
            
            cursor = conn.cursor()
            cursor.execute(f'SET SCHEMA "{schema}"')
            
            # Fetch customers only (CardType = 'C')
            limit_clause = f"LIMIT {limit}" if limit else ""
            cursor.execute(f'''
                SELECT 
                    "CardCode",
                    "CardName",
                    "Phone1",
                    "Cellular",
                    "E_Mail",
                    "Address",
                    "City",
                    "validFor"
                FROM "OCRD"
                WHERE "CardType" = 'C'
                ORDER BY "CardCode"
                {limit_clause}
            ''')
            
            customers = cursor.fetchall()
            
            self.stdout.write(f"Found {len(customers)} customers in {schema}")
            
            # Get company instance
            from FieldAdvisoryService.models import Company, Dealer
            
            try:
                company = Company.objects.get(name=company_key)
            except Company.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Company '{company_key}' not found in database. Skipping schema.")
                )
                continue
            
            for cust in customers:
                total_processed += 1
                
                card_code = (cust[0] or '').strip()
                card_name = (cust[1] or '').strip() or 'Unknown Customer'
                phone1 = (cust[2] or '').strip()
                cellular = (cust[3] or '').strip()
                email = (cust[4] or '').strip().lower()
                address = (cust[5] or '').strip() or 'N/A'
                city = (cust[6] or '').strip()
                is_active = cust[7] == 'Y'
                
                # Use phone or generate dummy
                contact_number = cellular or phone1 or f"000-{card_code[-7:]}"
                
                # Generate dummy CNIC (13 digits)
                # Use card_code numeric part
                card_numeric = ''.join(filter(str.isdigit, card_code))
                if len(card_numeric) < 13:
                    card_numeric = card_numeric.ljust(13, '0')
                cnic_number = card_numeric[:13]
                
                try:
                    if not dry_run:
                        with transaction.atomic():
                            dealer, created = Dealer.objects.update_or_create(
                                card_code=card_code,
                                defaults={
                                    'name': card_name[:100],  # Max length 100
                                    'cnic_number': cnic_number,
                                    'contact_number': contact_number[:20],  # Max length 20
                                    'company': company,
                                    'address': address[:500] if len(address) > 500 else address,
                                    'remarks': f"Imported from SAP {schema}",
                                    'is_active': is_active,
                                }
                            )
                            
                            if created:
                                total_created += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"  ✓ Created: {card_code} - {card_name[:50]}")
                                )
                            else:
                                total_updated += 1
                                self.stdout.write(
                                    self.style.WARNING(f"  ✓ Updated: {card_code} - {card_name[:50]}")
                                )
                    else:
                        self.stdout.write(f"  [DRY RUN] Would process: {card_code} - {card_name[:50]}")
                        
                except Exception as e:
                    total_skipped += 1
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Error processing {card_code}: {str(e)}")
                    )
            
            cursor.close()
        
        conn.close()
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("Import Summary"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"Total Processed: {total_processed}")
        self.stdout.write(self.style.SUCCESS(f"Created: {total_created}"))
        self.stdout.write(self.style.WARNING(f"Updated: {total_updated}"))
        self.stdout.write(self.style.ERROR(f"Skipped/Errors: {total_skipped}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n*** DRY RUN - No changes were saved ***"))

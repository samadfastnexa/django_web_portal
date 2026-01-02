"""
Django management command to import employees from SAP HANA 4B-ORANG_APP schema to User and SalesStaffProfile models
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from hdbcli import dbapi
import os
from dotenv import load_dotenv

load_dotenv()

User = get_user_model()


class Command(BaseCommand):
    help = 'Import employees from SAP HANA 4B-ORANG_APP schema to Django User and SalesStaffProfile models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving to database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        schema = '4B-ORANG_APP'
        company_key = '4B-ORANG'
        
        conn = dbapi.connect(
            address=os.getenv('HANA_HOST'),
            port=int(os.getenv('HANA_PORT')),
            user=os.getenv('HANA_USER'),
            password=os.getenv('HANA_PASSWORD')
        )

        total_processed = 0
        total_created = 0
        total_updated = 0
        total_skipped = 0

        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS(f"Processing Schema: {schema} (Company: {company_key})"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))
        
        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        
        # Fetch active employees
        cursor.execute('''
            SELECT 
                "empID",
                "firstName",
                "middleName",
                "lastName",
                "email",
                "mobile",
                "homeTel",
                "officeExt",
                "Active",
                "startDate",
                "dept",
                "position",
                "jobTitle",
                "U_TERR",
                "U_HOD"
            FROM "OHEM"
            WHERE "Active" = 'Y'
            ORDER BY "empID"
        ''')
        
        employees = cursor.fetchall()
        
        self.stdout.write(f"Found {len(employees)} active employees in {schema}")
        
        for emp in employees:
            total_processed += 1
            
            emp_id = emp[0]
            first_name = (emp[1] or '').strip() or 'Employee'
            middle_name = (emp[2] or '').strip()
            last_name = (emp[3] or '').strip() or str(emp_id)
            email = (emp[4] or '').strip().lower() or f"emp{emp_id}@4bgroup.com"
            mobile = (emp[5] or '').strip()
            home_tel = (emp[6] or '').strip()
            office_ext = (emp[7] or '').strip()
            is_active = emp[8] == 'Y'
            start_date = emp[9]
            dept = emp[10]
            position = emp[11]
            job_title = (emp[12] or '').strip()
            territory_code = emp[13]
            hod_emp_id = emp[14]
            
            # Generate username from email
            username = email.split('@')[0]
            
            employee_code = f"{company_key}-EMP{emp_id}"
            
            try:
                if not dry_run:
                    with transaction.atomic():
                        from accounts.models import SalesStaffProfile
                        
                        sales_profile = SalesStaffProfile.objects.filter(
                            employee_code=employee_code
                        ).first()
                        
                        if sales_profile and sales_profile.user:
                            # Update existing user
                            user = sales_profile.user
                            user.first_name = first_name
                            user.last_name = last_name
                            user.is_active = is_active
                            user.is_sales_staff = True
                            user.save()
                            
                            # Update profile
                            sales_profile.phone_number = mobile or home_tel or 'N/A'
                            sales_profile.address = f"Dept: {dept}, Position: {position}"
                            sales_profile.designation = 'TSO'
                            sales_profile.save()
                            
                            total_updated += 1
                            self.stdout.write(
                                self.style.WARNING(f"  ✓ Updated: {employee_code} - {email}")
                            )
                        else:
                            # Create new user
                            user, created = User.objects.get_or_create(
                                email=email,
                                defaults={
                                    'username': username,
                                    'first_name': first_name,
                                    'last_name': last_name,
                                    'is_active': is_active,
                                    'is_sales_staff': True,
                                }
                            )
                            
                            if not created:
                                user.is_sales_staff = True
                                user.save()
                            
                            # Create or update SalesStaffProfile
                            sales_profile, profile_created = SalesStaffProfile.objects.update_or_create(
                                employee_code=employee_code,
                                defaults={
                                    'user': user,
                                    'phone_number': mobile or home_tel or 'N/A',
                                    'address': f"Dept: {dept}, Position: {position}",
                                    'designation': 'TSO',
                                }
                            )
                            
                            if profile_created:
                                total_created += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"  ✓ Created: {employee_code} - {email}")
                                )
                            else:
                                total_updated += 1
                                self.stdout.write(
                                    self.style.WARNING(f"  ✓ Updated: {employee_code} - {email}")
                                )
                else:
                    self.stdout.write(f"  [DRY RUN] Would process: {employee_code} - {email}")
                    
            except Exception as e:
                total_skipped += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error processing {employee_code}: {str(e)}")
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

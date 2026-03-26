"""
Django management command to import sales staff from CSV file.
Features:
- Upsert logic: Update if exists, Insert if new (by employee_code)
- Validates employee codes for duplicates
- Preserves existing employees not in import file
- Handles ManyToMany relationships (regions, zones, territories, companies)
- Detailed logging of all operations
"""

import csv
import re
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pathlib import Path
from accounts.models import SalesStaffProfile, DesignationModel, User, Role
from FieldAdvisoryService.models import Region, Zone, Territory, Company


class Command(BaseCommand):
    help = 'Import sales staff from CSV file with upsert logic (update if exists, insert if new)'

    def _clean_alpha(self, value, fallback=''):
        cleaned = re.sub(r'[^A-Za-z\s]+', ' ', (value or '').strip())
        cleaned = ' '.join(cleaned.split())
        return cleaned or fallback

    def _split_name(self, full_name, emp_code):
        tokens = [t for t in (full_name or '').strip().split() if t]
        first = self._clean_alpha(tokens[0] if tokens else 'Employee', 'Employee')
        last_raw = ' '.join(tokens[1:]) if len(tokens) > 1 else f'Staff {emp_code}'
        last = self._clean_alpha(last_raw, f'Staff {emp_code}')
        return first[:150], last[:150]

    def _make_unique_email(self, email, emp_code):
        base_email = (email or '').strip().lower()
        if base_email and not User.objects.filter(email__iexact=base_email).exists():
            return base_email

        candidate = f'sales_{emp_code}@4b.local'
        idx = 1
        while User.objects.filter(email__iexact=candidate).exists():
            candidate = f'sales_{emp_code}_{idx}@4b.local'
            idx += 1
        return candidate

    def _make_unique_username(self, base):
        username = re.sub(r'[^a-zA-Z0-9._+-]+', '', (base or '').lower()) or 'sales_user'
        username = username[:150]
        candidate = username
        idx = 1
        while User.objects.filter(username__iexact=candidate).exists():
            suffix = str(idx)
            candidate = f"{username[:max(1, 150-len(suffix))]}{suffix}"
            idx += 1
        return candidate

    def _make_available_phone(self, phone):
        value = (phone or '').strip()
        if not value:
            return None
        # Keep source formatting but avoid unique collisions.
        if User.objects.filter(phone_number=value).exists():
            return None
        return value

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without making changes'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options.get('dry_run', False)

        # Validate file exists
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise CommandError(f'CSV file not found: {csv_file}')

        # Read and validate CSV
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('SALES STAFF IMPORT - VALIDATION'))
        self.stdout.write(self.style.SUCCESS('='*70))

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            raise CommandError(f'Error reading CSV: {str(e)}')

        if not rows:
            raise CommandError('CSV file is empty')

        self.stdout.write(f'CSV Records: {len(rows)}')

        # Check for duplicates
        emp_codes = [r['EmpCode'].strip() for r in rows if r['EmpCode'].strip()]
        seen = set()
        duplicates = []
        for code in emp_codes:
            if code in seen:
                duplicates.append(code)
            seen.add(code)

        if duplicates:
            raise CommandError(f'Duplicate employee codes found in CSV: {duplicates}')

        self.stdout.write(self.style.SUCCESS('No duplicates in CSV - OK\n'))

        # Summary
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('IMPORT PLAN'))
        self.stdout.write(self.style.SUCCESS('='*70))

        existing_count = SalesStaffProfile.objects.filter(
            employee_code__in=emp_codes
        ).count()
        new_count = len(emp_codes) - existing_count

        self.stdout.write(f'Total to import: {len(emp_codes)}')
        self.stdout.write(f'Will UPDATE: {existing_count} existing records')
        self.stdout.write(f'Will CREATE: {new_count} new records')
        self.stdout.write(f'Dry run: {dry_run}\n')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            return

        # Import with transaction
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('IMPORTING DATA'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        created_count = 0
        updated_count = 0
        created_users = 0
        linked_existing_users = 0
        errors = []
        default_role = Role.objects.filter(name='FirstRole').first() or Role.objects.first()

        with transaction.atomic():
            for idx, row in enumerate(rows, 1):
                try:
                    emp_code = row['EmpCode'].strip()
                    emp_name = row['EmployeeName'].strip()
                    designation_name = row['Designation'].strip() or 'Farmer Service Manager'
                    mobile = row['MobileNo'].strip() or None
                    region = row['Region'].strip() or None
                    zone = row['Zone'].strip() or None
                    territory = row['Territory'].strip() or None
                    company = row['Company'].strip() or None

                    # Get or create designation (handle empty codes safely)
                    if designation_name and designation_name.strip():
                        try:
                            designation = DesignationModel.objects.get(name__iexact=designation_name)
                        except DesignationModel.DoesNotExist:
                            # Try to create with proper code handling
                            try:
                                # Generate a code from the name (first 2 letters + unique suffix)
                                base_code = ''.join(word[0] for word in designation_name.split())[:3].upper()
                                if not base_code:
                                    base_code = 'DSN'
                                
                                # Check if code exists
                                existing = DesignationModel.objects.filter(code=base_code).exists()
                                if existing:
                                    # If it exists, find the existing one and use it
                                    designation = DesignationModel.objects.get(code=base_code)
                                else:
                                    # Create new with the code
                                    designation, _ = DesignationModel.objects.get_or_create(
                                        code=base_code,
                                        defaults={'name': designation_name}
                                    )
                            except DesignationModel.MultipleObjectsReturned:
                                # Use first match if multiple exist
                                designation = DesignationModel.objects.filter(name__iexact=designation_name).first()
                            except Exception as e:
                                # If all else fails, use default
                                designation = DesignationModel.objects.filter(name='Farmer Service Manager').first() or \
                                              DesignationModel.objects.first()
                        except DesignationModel.MultipleObjectsReturned:
                            # Use first match if multiple exist
                            designation = DesignationModel.objects.filter(name__iexact=designation_name).first()
                    else:
                        # Use default if empty
                        designation = DesignationModel.objects.filter(name='Farmer Service Manager').first() or \
                                      DesignationModel.objects.first()

                    # Update or create
                    profile, created = SalesStaffProfile.objects.update_or_create(
                        employee_code=emp_code,
                        defaults={
                            'phone_number': mobile,
                            'designation': designation,
                        }
                    )

                    # Handle ManyToMany relationships
                    # Clear existing and repopulate
                    profile.regions.clear()
                    profile.zones.clear()
                    profile.territories.clear()
                    profile.companies.clear()

                    # Add region if exists (handle multiple matches)
                    if region and region != '0':
                        try:
                            region_objs = Region.objects.filter(name__iexact=region)[:1]
                            if region_objs:
                                profile.regions.add(region_objs[0])
                        except Exception:
                            pass  # Region not found or other error, skip

                    # Add zone if exists (handle multiple matches)
                    if zone and zone != '0' and zone != '-':
                        try:
                            zone_objs = Zone.objects.filter(name__iexact=zone)[:1]
                            if zone_objs:
                                profile.zones.add(zone_objs[0])
                        except Exception:
                            pass  # Zone not found or other error, skip

                    # Add territory if exists (handle multiple matches)
                    if territory and territory != '0' and territory != '-':
                        try:
                            territory_objs = Territory.objects.filter(name__iexact=territory)[:1]
                            if territory_objs:
                                profile.territories.add(territory_objs[0])
                        except Exception:
                            pass  # Territory not found or other error, skip

                    # Add company if exists (handle multiple matches)
                    if company and company != '0':
                        try:
                            company_objs = Company.objects.filter(name__iexact=company)[:1]
                            if company_objs:
                                profile.companies.add(company_objs[0])
                        except Exception:
                            pass  # Company not found or other error, skip

                    # Ensure a User account is linked so staff appears in User admin.
                    if not profile.user_id:
                        incoming_email = (row.get('Email') or '').strip().lower()
                        existing_user = None
                        if incoming_email:
                            maybe_user = User.objects.filter(email__iexact=incoming_email).first()
                            # OneToOne safety: don't re-link if user already belongs to another profile.
                            if maybe_user and not hasattr(maybe_user, 'sales_profile'):
                                existing_user = maybe_user

                        if existing_user:
                            existing_user.is_sales_staff = True
                            existing_user.is_active = True
                            if default_role and not existing_user.role_id:
                                existing_user.role = default_role
                            if company and not existing_user.company_id:
                                company_obj = Company.objects.filter(name__iexact=company).first()
                                if company_obj:
                                    existing_user.company = company_obj
                            existing_user.save()
                            profile.user = existing_user
                            profile.save(update_fields=['user'])
                            linked_existing_users += 1
                        else:
                            first_name, last_name = self._split_name(emp_name, emp_code)
                            final_email = self._make_unique_email(incoming_email, emp_code)
                            username_base = final_email.split('@')[0]
                            username = self._make_unique_username(username_base)
                            phone_for_user = self._make_available_phone(mobile)
                            company_obj = Company.objects.filter(name__iexact=company).first() if company else None

                            new_user = User.objects.create(
                                email=final_email,
                                username=username,
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_for_user,
                                company=company_obj,
                                role=default_role,
                                is_active=True,
                                is_sales_staff=True,
                                is_dealer=False,
                                is_staff=False,
                            )
                            new_user.set_unusable_password()
                            new_user.save(update_fields=['password'])
                            profile.user = new_user
                            profile.save(update_fields=['user'])
                            created_users += 1

                    if created:
                        created_count += 1
                        status = 'CREATED'
                    else:
                        updated_count += 1
                        status = 'UPDATED'

                    if idx % 20 == 0 or idx == 1:
                        self.stdout.write(f'[{idx}/{len(rows)}] {status}: Code={emp_code} Name={emp_name}')

                except Exception as e:
                    errors.append({
                        'row': idx,
                        'code': emp_code,
                        'error': str(e)
                    })
                    self.stdout.write(self.style.ERROR(f'ERROR at row {idx}: {str(e)}'))

        # Final report
        self.stdout.write('\n' + self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count} new records'))
        self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count} existing records'))
        self.stdout.write(self.style.SUCCESS(f'Total: {created_count + updated_count} records processed'))
        self.stdout.write(self.style.SUCCESS(f'Linked existing users: {linked_existing_users}'))
        self.stdout.write(self.style.SUCCESS(f'Created users: {created_users}'))

        if errors:
            self.stdout.write(self.style.ERROR(f'\nErrors: {len(errors)} records failed'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  Row {error['row']} (Code {error['code']}): {error['error']}"))
        else:
            self.stdout.write(self.style.SUCCESS('\nNo errors - all records imported successfully!\n'))

"""
Management command to generate passwords for sales staff users and export to CSV.

Password format: FirstName-XXXXXX
  - FirstName: user's first_name with spaces removed (e.g. "Shahbaz Haider" → "ShahbazHaider")
  - XXXXXX: 6 random uppercase alphanumeric characters

Usage:
    python manage.py generate_passwords
    python manage.py generate_passwords --output passwords_output.csv
    python manage.py generate_passwords --overwrite          # re-generate even if password already set
    python manage.py generate_passwords --emp-code 1931 3059 # specific employees only
    python manage.py generate_passwords --dry-run            # preview without saving
"""

import csv
import random
import string
import os
from pathlib import Path
from django.core.management.base import BaseCommand

from accounts.models import SalesStaffProfile, User


def _random_suffix(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def _build_password(first_name: str) -> str:
    name_part = (first_name or '').replace(' ', '')
    return f"{name_part}-{_random_suffix()}"


class Command(BaseCommand):
    help = 'Generate passwords for sales staff users and export to CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='passwords_output.csv',
            help='Path for the output CSV file (default: passwords_output.csv)',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Re-generate password even if user already has one set',
        )
        parser.add_argument(
            '--emp-code',
            nargs='+',
            type=str,
            dest='emp_codes',
            help='Limit to specific employee codes',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview generated passwords without saving to DB',
        )

    def handle(self, *args, **options):
        output_path = Path(options['output'])
        overwrite = options['overwrite']
        emp_codes = options.get('emp_codes')
        dry_run = options['dry_run']

        self.stdout.write('=' * 70)
        self.stdout.write('SALES STAFF PASSWORD GENERATOR')
        self.stdout.write('=' * 70)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes will be saved to the database'))

        # Build queryset
        qs = SalesStaffProfile.objects.select_related('user').filter(
            user__isnull=False,
            is_vacant=False,
        )
        if emp_codes:
            qs = qs.filter(employee_code__in=emp_codes)

        profiles = list(qs)
        if not profiles:
            self.stdout.write(self.style.WARNING('No matching sales staff profiles found.'))
            return

        self.stdout.write(f'Profiles to process: {len(profiles)}')

        rows = []
        generated = 0
        skipped = 0

        for profile in profiles:
            user: User = profile.user

            # Skip if already has a usable password and --overwrite not set
            has_password = user.has_usable_password()
            if has_password and not overwrite:
                skipped += 1
                continue

            plain_password = _build_password(user.first_name)

            if not dry_run:
                user.set_password(plain_password)
                user.save(update_fields=['password'])

            rows.append({
                'EmpCode': profile.employee_code or '',
                'FullName': f"{user.first_name} {user.last_name}".strip(),
                'Username': user.username,
                'Email': user.email,
                'PhoneNumber': user.phone_number or '',
                'Password': plain_password,
            })
            generated += 1

        # Write CSV
        if rows:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['EmpCode', 'FullName', 'Username', 'Email', 'PhoneNumber', 'Password'])
                writer.writeheader()
                writer.writerows(rows)

            abs_path = output_path.resolve()
            self.stdout.write(self.style.SUCCESS(f'\nCSV saved to: {abs_path}'))
        else:
            self.stdout.write(self.style.WARNING('\nNo passwords generated - all users already have passwords. Use --overwrite to regenerate.'))

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Generated : {generated}')
        self.stdout.write(f'Skipped (already has password): {skipped}')
        self.stdout.write(f'Total profiles found: {len(profiles)}')

        # Preview first few rows
        if rows:
            self.stdout.write('\nSample (first 10 rows):')
            self.stdout.write(f"{'EmpCode':<10} {'FullName':<30} {'Password':<25}")
            self.stdout.write('-' * 65)
            for row in rows[:10]:
                self.stdout.write(f"{row['EmpCode']:<10} {row['FullName']:<30} {row['Password']:<25}")

"""
Management command to import dealers from SAP HANA 4B-ORANG_LIVE schema.

- Upsert logic: update existing dealers by card_code, create new ones
- Creates linked User accounts with generated passwords
- Skips validation (no CNIC/profile_image required for SAP imports)
- Generates orange_dealers_passwords.csv

Usage:
    python manage.py import_orange_dealers
    python manage.py import_orange_dealers --dry-run
    python manage.py import_orange_dealers --output /path/to/output.csv
"""

import csv
import random
import string
import re
from pathlib import Path
from django.core.management.base import BaseCommand


def _random_suffix(k=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=k))


def _generate_password(card_name: str) -> str:
    first = (card_name or 'Dealer').split()[0]
    return f"{first}-{_random_suffix()}"


def _format_cnic(card_code: str) -> str:
    """
    Build a fake CNIC in XXXXX-XXXXXXX-X format from card_code digits.
    Pads / truncates to exactly 13 digits then formats.
    """
    digits = re.sub(r'\D', '', card_code).ljust(13, '0')[:13]
    return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"


def _unique_email(base_email: str, card_code: str, User):
    """Return a unique email, falling back to a local address if taken."""
    if base_email:
        if not User.objects.filter(email__iexact=base_email).exists():
            return base_email
    candidate = f"dealer_{card_code.lower()}@orangeprotection.local"
    idx = 1
    while User.objects.filter(email__iexact=candidate).exists():
        candidate = f"dealer_{card_code.lower()}_{idx}@orangeprotection.local"
        idx += 1
    return candidate


def _unique_dealer_contact(contact: str, card_code: str, Dealer):
    """
    Return a unique contact_number for the Dealer table.
    If the value is empty, a dash, or already taken, generate a safe placeholder.
    """
    from FieldAdvisoryService.models import Dealer as DealerModel
    def _taken(val):
        return DealerModel.objects.filter(contact_number=val).exists()

    if contact and contact.strip() not in ('', '-') and not _taken(contact):
        return contact

    # Generate placeholder from card_code
    placeholder = f"00-{card_code}"
    idx = 1
    while _taken(placeholder):
        placeholder = f"00-{card_code}-{idx}"
        idx += 1
    return placeholder


def _unique_cnic(cnic: str, card_code: str, Dealer):
    """Return a unique CNIC, appending index suffix if already taken."""
    if not Dealer.objects.filter(cnic_number=cnic).exists():
        return cnic
    idx = 1
    while True:
        digits = re.sub(r'\D', '', card_code + str(idx)).ljust(13, '0')[:13]
        candidate = f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
        if not Dealer.objects.filter(cnic_number=candidate).exists():
            return candidate
        idx += 1


class Command(BaseCommand):
    help = 'Import dealers from SAP HANA 4B-ORANG_LIVE and create user accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='orange_dealers_passwords.csv',
            help='Output CSV file path (default: orange_dealers_passwords.csv)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Fetch from SAP and preview without saving to DB',
        )

    def handle(self, *args, **options):
        from FieldAdvisoryService.models import Company, Dealer
        from accounts.models import User, Role

        output_path = Path(options['output'])
        dry_run = options['dry_run']
        schema = '4B-ORANG_LIVE'

        self.stdout.write('=' * 65)
        self.stdout.write(f'ORANGE DEALERS IMPORT  —  schema: {schema}')
        self.stdout.write('=' * 65)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no DB changes will be made'))

        # ── Connect to SAP HANA ──────────────────────────────────────
        try:
            from hdbcli import dbapi
            from decouple import config as env
            conn = dbapi.connect(
                address=env('HANA_HOST'),
                port=int(env('HANA_PORT', default='30015')),
                user=env('HANA_USER'),
                password=env('HANA_PASSWORD'),
            )
            self.stdout.write(self.style.SUCCESS('Connected to SAP HANA'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'SAP HANA connection failed: {e}'))
            return

        cursor = conn.cursor()
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.execute('''
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
            WHERE "CardType" = \'C\'
            ORDER BY "CardCode"
        ''')
        customers = cursor.fetchall()
        conn.close()
        self.stdout.write(f'Records fetched from SAP: {len(customers)}\n')

        if not customers:
            self.stdout.write(self.style.WARNING('No dealers found in SAP.'))
            return

        # ── Get / create Company ─────────────────────────────────────
        from django.db.models import Q
        company = Company.objects.filter(
            Q(name=schema) | Q(Company_name__icontains='Orange')
        ).first()
        if not company and not dry_run:
            company, _ = Company.objects.get_or_create(
                name=schema,
                defaults={
                    'Company_name': 'Orange Protection',
                    'description': 'Orange Protection - Imported from SAP HANA',
                    'address': 'Head Office',
                    'email': 'info@orangeprotection.com',
                },
            )
            self.stdout.write(self.style.SUCCESS(f'Created company: {company.Company_name}'))
        elif company:
            self.stdout.write(self.style.SUCCESS(f'Using company: {company.Company_name} ({company.name})'))
        else:
            self.stdout.write(self.style.WARNING('Company not found (dry-run, skipping creation)'))

        default_role = Role.objects.filter(name='FirstRole').first()

        # ── Process each dealer ──────────────────────────────────────
        csv_rows = []
        created_count = updated_count = error_count = 0

        for row in customers:
            card_code  = (row[0] or '').strip()
            card_name  = (row[1] or '').strip() or 'Unknown Dealer'
            phone1     = (row[2] or '').strip()
            cellular   = (row[3] or '').strip()
            raw_email  = (row[4] or '').strip().lower()
            address    = (row[5] or '').strip() or 'N/A'
            city       = (row[6] or '').strip()
            is_active  = row[7] == 'Y'

            if not card_code:
                continue

            contact = cellular or phone1
            name_parts = card_name.split(' ', 1)
            first_name = name_parts[0][:150]
            last_name  = (name_parts[1] if len(name_parts) > 1 else '')[:150]

            password = _generate_password(card_name)

            if dry_run:
                csv_rows.append({
                    'CardCode':   card_code,
                    'DealerName': card_name,
                    'Username':   card_code,
                    'Email':      raw_email or f"dealer_{card_code.lower()}@orangeprotection.local",
                    'PhoneNumber': contact,
                    'Password':   password,
                    'City':       city,
                    'Status':     'Active' if is_active else 'Inactive',
                })
                continue

            try:
                # ── User ──────────────────────────────────────────────
                email           = _unique_email(raw_email, card_code, User)
                dealer_contact  = _unique_dealer_contact(contact, card_code, Dealer)
                cnic            = _unique_cnic(_format_cnic(card_code), card_code, Dealer)

                user, user_created = User.objects.get_or_create(
                    username=card_code,
                    defaults={
                        'email':          email,
                        'first_name':     first_name,
                        'last_name':      last_name,
                        'phone_number':   None,   # phone stored on Dealer, not User
                        'is_active':      True,
                        'is_staff':       False,
                        'is_sales_staff': False,
                        'is_dealer':      True,
                        'role':           default_role,
                        'company':        company,
                    },
                )
                if user_created:
                    user.set_password(password)
                    user.save(update_fields=['password'])

                # ── Dealer ────────────────────────────────────────────
                dealer, dealer_created = Dealer.objects.update_or_create(
                    card_code=card_code,
                    defaults={
                        'cnic_number':    cnic,
                        'contact_number': dealer_contact[:20],
                        'company':        company,
                        'address':        address[:500],
                        'city':           city[:100] if city else '',
                        'remarks':        f'Imported from SAP {schema}',
                        'is_active':      is_active,
                        'user':           user,
                    },
                )

                if dealer_created:
                    created_count += 1
                    status_str = 'CREATED'
                else:
                    updated_count += 1
                    status_str = 'UPDATED'

                csv_rows.append({
                    'CardCode':    card_code,
                    'DealerName':  card_name,
                    'Username':    user.username,
                    'Email':       user.email,
                    'PhoneNumber': contact or dealer_contact,
                    'Password':    password if user_created else '(existing user)',
                    'City':        city,
                    'Status':      'Active' if is_active else 'Inactive',
                })

                if (created_count + updated_count) % 50 == 0 or (created_count + updated_count) == 1:
                    self.stdout.write(f'  [{status_str}] {card_code} — {card_name[:45]}')

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  [ERROR] {card_code}: {str(e)[:80]}'))

        # ── Write CSV ────────────────────────────────────────────────
        if csv_rows:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'CardCode', 'DealerName', 'Username', 'Email',
                    'PhoneNumber', 'Password', 'City', 'Status',
                ])
                writer.writeheader()
                writer.writerows(csv_rows)
            self.stdout.write(self.style.SUCCESS(f'\nCSV saved: {output_path.resolve()}'))

        # ── Summary ──────────────────────────────────────────────────
        self.stdout.write('\n' + '=' * 65)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 65)
        self.stdout.write(f'Total fetched from SAP : {len(customers)}')
        if not dry_run:
            self.stdout.write(f'Dealers created        : {created_count}')
            self.stdout.write(f'Dealers updated        : {updated_count}')
            self.stdout.write(f'Errors                 : {error_count}')
        self.stdout.write(f'CSV rows written       : {len(csv_rows)}')

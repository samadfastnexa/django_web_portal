from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from farmers.models import Farmer
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Link existing farmers to User accounts and create user accounts for farmers without one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making any changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Get all farmers
        farmers = Farmer.objects.all()
        total_farmers = farmers.count()
        
        stats = {
            'total': total_farmers,
            'already_linked': 0,
            'linked_existing': 0,
            'created_new': 0,
            'errors': 0,
            'skipped_no_phone': 0,
        }
        
        self.stdout.write(f'\n📊 Found {total_farmers} farmers in total\n')
        
        for farmer in farmers:
            try:
                # Check if farmer already has a user
                if farmer.user:
                    stats['already_linked'] += 1
                    self.stdout.write(f'  ✓ {farmer.name} ({farmer.farmer_id}) already linked to user')
                    continue
                
                # Check if farmer has a phone number
                if not farmer.primary_phone:
                    stats['skipped_no_phone'] += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ {farmer.name} ({farmer.farmer_id}) has no phone number - skipped'
                        )
                    )
                    continue
                
                # Try to find existing user with this phone as username
                try:
                    existing_user = User.objects.get(username=farmer.primary_phone)
                    
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [DRY RUN] Would link {farmer.name} to existing user {existing_user.email}'
                            )
                        )
                    else:
                        farmer.user = existing_user
                        farmer.save()
                        stats['linked_existing'] += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Linked {farmer.name} ({farmer.farmer_id}) to existing user {existing_user.email}'
                            )
                        )
                except User.DoesNotExist:
                    # Create new user
                    default_password = farmer.cnic[-4:] if farmer.cnic and len(farmer.cnic) >= 4 else 'farmer1234'
                    email = farmer.email if farmer.email else f'{farmer.primary_phone}@farmer.local'
                    
                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [DRY RUN] Would create user for {farmer.name} (phone: {farmer.primary_phone}, password: {default_password})'
                            )
                        )
                    else:
                        with transaction.atomic():
                            new_user = User.objects.create_user(
                                username=farmer.primary_phone,
                                email=email,
                                password=default_password,
                                first_name=farmer.first_name,
                                last_name=farmer.last_name,
                                is_active=True
                            )
                            
                            # Set farmer flag if exists
                            if hasattr(new_user, 'is_farmer'):
                                new_user.is_farmer = True
                                new_user.save(update_fields=['is_farmer'])
                            
                            farmer.user = new_user
                            farmer.save()
                            
                            stats['created_new'] += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ Created user for {farmer.name} ({farmer.farmer_id}) - phone: {farmer.primary_phone}, password: {default_password}'
                                )
                            )
            
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Error for {farmer.name} ({farmer.farmer_id}): {str(e)}'
                    )
                )
        
        # Print summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('\n📈 SUMMARY:\n'))
        self.stdout.write(f'  Total farmers: {stats["total"]}')
        self.stdout.write(f'  Already linked: {stats["already_linked"]}')
        self.stdout.write(f'  Linked to existing users: {stats["linked_existing"]}')
        self.stdout.write(f'  New users created: {stats["created_new"]}')
        self.stdout.write(f'  Skipped (no phone): {stats["skipped_no_phone"]}')
        self.stdout.write(f'  Errors: {stats["errors"]}')
        self.stdout.write('='*70 + '\n')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\n💡 This was a dry run. Run without --dry-run to apply changes.\n'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Migration completed!\n'))
            
            if stats['created_new'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'\n📝 NOTE: {stats["created_new"]} farmers can now login with:\n'
                        '   - Phone number as username\n'
                        '   - Password: Last 4 digits of CNIC (or "farmer1234" if no CNIC)\n'
                        '   - They should change their password after first login\n'
                    )
                )

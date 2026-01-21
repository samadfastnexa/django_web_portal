from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart, CartItem


class Command(BaseCommand):
    help = 'Clean up expired cart items (older than 24 hours)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours after which items expire (default: 24)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n🧹 CLEANING UP EXPIRED CART ITEMS\n{"="*60}\n'
        ))
        
        # Calculate expiry time
        expiry_time = timezone.now() - timedelta(hours=hours)
        self.stdout.write(f'Expiry threshold: {expiry_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Items older than {hours} hours will be removed\n')
        
        # Find expired items
        expired_items = CartItem.objects.filter(
            created_at__lt=expiry_time,
            is_active=True
        )
        
        total_count = expired_items.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No expired items found!'))
            return
        
        # Group by cart for better reporting
        carts_affected = expired_items.values_list('cart__user__email', flat=True).distinct()
        
        self.stdout.write(f'\nFound {total_count} expired items in {len(carts_affected)} carts:')
        
        # Show details
        for email in carts_affected:
            items = expired_items.filter(cart__user__email=email)
            self.stdout.write(f'\n  📧 {email}:')
            for item in items:
                age_hours = (timezone.now() - item.created_at).total_seconds() / 3600
                self.stdout.write(
                    f'    - {item.product_name} (x{item.quantity}) '
                    f'[Age: {age_hours:.1f} hours]'
                )
        
        # Perform cleanup
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  DRY RUN MODE - No items were actually deleted'
            ))
        else:
            # Mark items as inactive instead of deleting
            expired_items.update(is_active=False)
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Successfully cleaned up {total_count} expired items!'
            ))
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}\n'))

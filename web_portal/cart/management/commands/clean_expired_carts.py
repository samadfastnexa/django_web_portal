"""
Management command to clean expired cart items.

This command removes cart items that have been inactive for more than 24 hours.
Run this command periodically via cron job or task scheduler.

Usage:
    python manage.py clean_expired_carts
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cart.models import Cart, CartItem


class Command(BaseCommand):
    help = 'Remove cart items that have been in cart for more than 24 hours'
    
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
            help='Number of hours after which to expire cart items (default: 24)',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hours = options['hours']
        
        self.stdout.write(f'Searching for cart items older than {hours} hours...')
        
        # Calculate expiry time
        expiry_time = timezone.now() - timedelta(hours=hours)
        
        # Find expired items
        expired_items = CartItem.objects.filter(
            created_at__lt=expiry_time,
            is_active=True
        )
        
        count = expired_items.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired cart items found.'))
            return
        
        # Show details
        self.stdout.write(f'Found {count} expired cart items:')
        
        for item in expired_items[:10]:  # Show first 10
            self.stdout.write(
                f'  - {item.product_name} (x{item.quantity}) in cart of {item.cart.user.email} '
                f'(added {item.created_at})'
            )
        
        if count > 10:
            self.stdout.write(f'  ... and {count - 10} more items')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would mark {count} items as inactive. '
                    'Run without --dry-run to actually clean them.'
                )
            )
        else:
            # Mark items as inactive
            expired_items.update(is_active=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully marked {count} expired cart items as inactive.'
                )
            )
            
            # Optionally, show statistics
            total_active_items = CartItem.objects.filter(is_active=True).count()
            self.stdout.write(f'Remaining active cart items: {total_active_items}')

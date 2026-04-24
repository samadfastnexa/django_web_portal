"""
Management command to clean up expired attachments.

Usage:
    python manage.py cleanup_expired_attachments
    python manage.py cleanup_expired_attachments --delete
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from document_management.models import Attachment


class Command(BaseCommand):
    help = 'Find and archive expired attachments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Archive expired attachments (set status to expired)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Archive attachments expiring within N days',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find expired attachments
        if options['days'] > 0:
            expiry_threshold = now + timezone.timedelta(days=options['days'])
            expired = Attachment.objects.filter(
                expiry_date__lt=expiry_threshold,
                status='active'
            )
            message = f"expiring within {options['days']} days"
        else:
            expired = Attachment.objects.filter(
                expiry_date__lt=now,
                status='active'
            )
            message = "already expired"
        
        count = expired.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f'No attachments {message}'))
            return
        
        # Display found attachments
        self.stdout.write(f'\nFound {count} attachment(s) {message}:\n')
        for attachment in expired:
            self.stdout.write(f'  - {attachment.title} (expires: {attachment.expiry_date})')
        
        # Archive if --delete flag is set
        if options['delete']:
            expired.update(status='expired')
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Archived {count} attachment(s)')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'\nRun with --delete to archive these attachments'
                )
            )

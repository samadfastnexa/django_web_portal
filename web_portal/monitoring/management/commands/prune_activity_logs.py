from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import ActivityLog


class Command(BaseCommand):
    help = 'Delete ActivityLog rows older than the given number of days (default 90).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete activity logs older than this many days (default: 90).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report how many rows would be deleted without deleting.',
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timedelta(days=days)
        qs = ActivityLog.objects.filter(timestamp__lt=cutoff)
        count = qs.count()

        if options['dry_run']:
            self.stdout.write(f'[dry-run] {count} activity log(s) older than {days} day(s) would be deleted.')
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Deleted {deleted} activity log(s) older than {days} day(s) (before {cutoff:%Y-%m-%d %H:%M}).'
        ))

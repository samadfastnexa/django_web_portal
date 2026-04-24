"""
Management command to generate attachment statistics report.

Usage:
    python manage.py attachment_stats
    python manage.py attachment_stats --user-id 5
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from document_management.models import Attachment, AttachmentAssignment

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate attachment statistics report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Show stats for a specific user',
        )

    def handle(self, *args, **options):
        if options['user_id']:
            self.user_stats(options['user_id'])
        else:
            self.overall_stats()

    def overall_stats(self):
        """Display overall system statistics."""
        total_attachments = Attachment.objects.count()
        active = Attachment.objects.filter(status='active').count()
        archived = Attachment.objects.filter(status='archived').count()
        expired = Attachment.objects.filter(status='expired').count()
        
        total_assignments = AttachmentAssignment.objects.count()
        viewed = AttachmentAssignment.objects.filter(viewed=True).count()
        acknowledged = AttachmentAssignment.objects.filter(acknowledged=True).count()
        total_downloads = sum(
            a.download_count for a in AttachmentAssignment.objects.all()
        )
        
        self.stdout.write(self.style.SUCCESS('\n=== ATTACHMENT STATISTICS ===\n'))
        
        self.stdout.write('Attachments:')
        self.stdout.write(f'  Total: {total_attachments}')
        self.stdout.write(f'  Active: {active}')
        self.stdout.write(f'  Archived: {archived}')
        self.stdout.write(f'  Expired: {expired}')
        
        self.stdout.write('\nAssignments:')
        self.stdout.write(f'  Total: {total_assignments}')
        self.stdout.write(f'  Viewed: {viewed} ({viewed/total_assignments*100:.1f}%)')
        self.stdout.write(f'  Acknowledged: {acknowledged} ({acknowledged/total_assignments*100:.1f}%)')
        self.stdout.write(f'  Total Downloads: {total_downloads}')
        
        # Top 5 most assigned attachments
        self.stdout.write('\nMost Assigned Attachments:')
        top_attachments = Attachment.objects.annotate(
            assignment_count=models.Count('assignments')
        ).order_by('-assignment_count')[:5]
        
        for att in top_attachments:
            self.stdout.write(f'  {att.title}: {att.assignment_count} users')
        
        self.stdout.write('')

    def user_stats(self, user_id):
        """Display statistics for a specific user."""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
            return
        
        assignments = AttachmentAssignment.objects.filter(user=user)
        total = assignments.count()
        viewed = assignments.filter(viewed=True).count()
        not_viewed = assignments.filter(viewed=False).count()
        acknowledged = assignments.filter(acknowledged=True).count()
        mandatory_pending = assignments.filter(
            attachment__is_mandatory=True,
            viewed=False
        ).count()
        total_downloads = sum(a.download_count for a in assignments)
        
        self.stdout.write(
            self.style.SUCCESS(f'\n=== STATS FOR USER: {user.username} ===\n')
        )
        
        self.stdout.write(f'Total Assigned: {total}')
        self.stdout.write(f'Viewed: {viewed} ({viewed/total*100:.1f}%)')
        self.stdout.write(f'Not Viewed: {not_viewed}')
        self.stdout.write(f'Acknowledged: {acknowledged}')
        self.stdout.write(
            self.style.WARNING(f'Mandatory Pending: {mandatory_pending}')
        )
        self.stdout.write(f'Total Downloads: {total_downloads}')
        
        if mandatory_pending > 0:
            self.stdout.write('\nMandatory Attachments Not Viewed:')
            pending = assignments.filter(
                attachment__is_mandatory=True,
                viewed=False
            )
            for assignment in pending:
                self.stdout.write(f'  - {assignment.attachment.title}')
        
        self.stdout.write('')


# Import models for annotation
from django.db import models

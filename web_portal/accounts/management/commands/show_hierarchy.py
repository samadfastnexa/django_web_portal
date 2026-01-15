"""
Management command to display the organizational hierarchy tree.

Usage:
    python manage.py show_hierarchy
    python manage.py show_hierarchy --company=1
    python manage.py show_hierarchy --user=5
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from FieldAdvisoryService.models import Company, UserHierarchy
from accounts.hierarchy_utils import print_hierarchy_tree, get_hierarchy_tree

User = get_user_model()


class Command(BaseCommand):
    help = 'Display the organizational hierarchy tree'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=int,
            help='Company ID to show hierarchy for'
        )
        parser.add_argument(
            '--user',
            type=int,
            help='User ID to start hierarchy from (shows this user and all subordinates)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['tree', 'json'],
            default='tree',
            help='Output format: tree (visual) or json (structured data)'
        )
    
    def handle(self, *args, **options):
        company_id = options.get('company')
        user_id = options.get('user')
        output_format = options.get('format')
        
        # Determine company
        if company_id:
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Company with ID {company_id} not found'))
                return
        else:
            # Get first company if only one exists
            companies = Company.objects.all()
            if companies.count() == 0:
                self.stdout.write(self.style.ERROR('No companies found in the system'))
                return
            elif companies.count() == 1:
                company = companies.first()
                self.stdout.write(self.style.WARNING(f'Using company: {company.Company_name}'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'Multiple companies found. Please specify --company=<id>\n'
                    f'Available companies:'
                ))
                for c in companies:
                    self.stdout.write(f'  ID {c.id}: {c.Company_name}')
                return
        
        # Determine root user if specified
        root_user = None
        if user_id:
            try:
                root_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                return
        
        # Get hierarchy data
        if output_format == 'json':
            import json
            tree_data = get_hierarchy_tree(company, root_user)
            self.stdout.write(json.dumps(tree_data, indent=2))
        else:
            # Print tree format
            if root_user:
                self.stdout.write(self.style.SUCCESS(
                    f'\nShowing hierarchy for {root_user.get_full_name() or root_user.username} '
                    f'and subordinates in {company.Company_name}\n'
                ))
            
            print_hierarchy_tree(company, root_user)
            
            # Show statistics
            self.show_statistics(company)
    
    def show_statistics(self, company):
        """Show hierarchy statistics"""
        total_users = UserHierarchy.objects.filter(company=company, is_active=True).count()
        levels = UserHierarchy.objects.filter(
            company=company, is_active=True
        ).values_list(
            'hierarchy_level__level_name', 'hierarchy_level__level_order'
        ).distinct().order_by('hierarchy_level__level_order')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Hierarchy Statistics'))
        self.stdout.write('='*60)
        self.stdout.write(f'Total users in hierarchy: {total_users}')
        self.stdout.write(f'Hierarchy levels: {len(levels)}')
        
        for level_name, level_order in levels:
            count = UserHierarchy.objects.filter(
                company=company,
                hierarchy_level__level_name=level_name,
                is_active=True
            ).count()
            self.stdout.write(f'  Level {level_order}: {level_name} - {count} users')
        
        # Show orphaned users (no reports_to)
        orphans = UserHierarchy.objects.filter(
            company=company,
            reports_to__isnull=True,
            is_active=True
        ).count()
        if orphans > 0:
            self.stdout.write(f'\nTop-level users (no manager): {orphans}')

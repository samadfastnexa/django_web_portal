from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from crop_management.models import Crop, CropVariety, YieldData, FarmingPractice, CropResearch


class Command(BaseCommand):
    help = 'Create user groups and permissions for Crop Management system'
    
    def handle(self, *args, **options):
        self.stdout.write('Setting up Crop Management user groups and permissions...')
        
        # Define groups and their permissions
        groups_permissions = {
            'R&D Team': {
                'description': 'Research and Development team with full access to crop management',
                'models': ['crop', 'cropvariety', 'yielddata', 'farmingpractice', 'cropresearch'],
                'permissions': ['add', 'change', 'delete', 'view']
            },
            'MIS Team': {
                'description': 'Management Information System team with analytics access',
                'models': ['crop', 'cropvariety', 'yielddata', 'farmingpractice', 'cropresearch'],
                'permissions': ['add', 'change', 'delete', 'view']
            },
            'Agricultural Experts': {
                'description': 'Agricultural experts who can manage farming practices',
                'models': ['crop', 'cropvariety', 'farmingpractice'],
                'permissions': ['add', 'change', 'view']
            },
            'Farm Managers': {
                'description': 'Farm managers who can view and add yield data',
                'models': ['crop', 'cropvariety', 'yielddata'],
                'permissions': ['add', 'change', 'view']
            },
            'Research Coordinators': {
                'description': 'Research coordinators who can manage research data',
                'models': ['crop', 'cropvariety', 'cropresearch'],
                'permissions': ['add', 'change', 'view']
            },
            'Managers': {
                'description': 'General managers with read access to all data',
                'models': ['crop', 'cropvariety', 'yielddata', 'farmingpractice', 'cropresearch'],
                'permissions': ['view']
            }
        }
        
        # Get content types for our models
        content_types = {
            'crop': ContentType.objects.get_for_model(Crop),
            'cropvariety': ContentType.objects.get_for_model(CropVariety),
            'yielddata': ContentType.objects.get_for_model(YieldData),
            'farmingpractice': ContentType.objects.get_for_model(FarmingPractice),
            'cropresearch': ContentType.objects.get_for_model(CropResearch),
        }
        
        created_groups = 0
        updated_groups = 0
        
        for group_name, group_config in groups_permissions.items():
            # Create or get the group
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                created_groups += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created group: {group_name}')
                )
            else:
                updated_groups += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated existing group: {group_name}')
                )
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add permissions for each model
            permissions_added = 0
            for model_name in group_config['models']:
                content_type = content_types[model_name]
                
                for perm_type in group_config['permissions']:
                    codename = f'{perm_type}_{model_name}'
                    
                    try:
                        permission = Permission.objects.get(
                            codename=codename,
                            content_type=content_type
                        )
                        group.permissions.add(permission)
                        permissions_added += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Permission {codename} not found for {model_name}'
                            )
                        )
            
            self.stdout.write(
                f'  Added {permissions_added} permissions to {group_name}'
            )
        
        # Create sample data if requested
        if self.confirm_action('Do you want to create sample crop data?'):
            self.create_sample_data()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSetup completed successfully!\n'
                f'Created {created_groups} new groups\n'
                f'Updated {updated_groups} existing groups\n\n'
                f'Available groups:\n'
                + '\n'.join([f'- {name}' for name in groups_permissions.keys()])
            )
        )
    
    def confirm_action(self, message):
        """Ask for user confirmation"""
        response = input(f'{message} (y/N): ').lower().strip()
        return response in ['y', 'yes']
    
    def create_sample_data(self):
        """Create sample crop data for testing"""
        self.stdout.write('Creating sample crop data...')
        
        # Sample crops
        sample_crops = [
            {
                'name': 'Wheat',
                'scientific_name': 'Triticum aestivum',
                'category': 'cereal',
                'growth_cycle_days': 120,
                'growth_season': 'rabi',
                'water_requirement': 'medium',
                'description': 'Major cereal crop grown in winter season'
            },
            {
                'name': 'Rice',
                'scientific_name': 'Oryza sativa',
                'category': 'cereal',
                'growth_cycle_days': 150,
                'growth_season': 'kharif',
                'water_requirement': 'high',
                'description': 'Primary staple food crop'
            },
            {
                'name': 'Cotton',
                'scientific_name': 'Gossypium hirsutum',
                'category': 'fiber',
                'growth_cycle_days': 180,
                'growth_season': 'kharif',
                'water_requirement': 'medium',
                'description': 'Major cash crop for textile industry'
            },
            {
                'name': 'Sugarcane',
                'scientific_name': 'Saccharum officinarum',
                'category': 'cash',
                'growth_cycle_days': 365,
                'growth_season': 'perennial',
                'water_requirement': 'high',
                'description': 'Sugar producing crop'
            }
        ]
        
        crops_created = 0
        for crop_data in sample_crops:
            crop, created = Crop.objects.get_or_create(
                name=crop_data['name'],
                defaults=crop_data
            )
            if created:
                crops_created += 1
                self.stdout.write(f'  Created crop: {crop.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {crops_created} sample crops')
        )
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-sample-data',
            action='store_true',
            help='Create sample crop data for testing',
        )
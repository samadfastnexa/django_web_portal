from django.core.management.base import BaseCommand
from crop_manage.models import Crop, CropStage
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate sample crop data with stages'
    
    def handle(self, *args, **options):
        self.stdout.write('Populating crop data with stages...')
        
        # Get or create a user for created_by field
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}
        )
        
        # Sample crop data with stages
        crops_data = [
            {
                'name': 'Wheat',
                'variety': 'HD-2967',
                'season': 'Rabi',
                'remarks': 'High yielding variety suitable for irrigated conditions',
                'stages': [
                    {
                        'stage_name': 'Pre-sowing Treatment',
                        'days_after_sowing': 0,
                        'brand': 'Bayer CropScience',
                        'active_ingredient': 'Thiram + Carboxin',
                        'dose_per_acre': '2.5 gm/kg seed',
                        'purpose': 'Seed treatment for disease protection'
                    },
                    {
                        'stage_name': 'First Irrigation',
                        'days_after_sowing': 21,
                        'brand': 'UPL',
                        'active_ingredient': 'Urea',
                        'dose_per_acre': '50 kg/acre',
                        'purpose': 'Crown root initiation and tillering'
                    },
                    {
                        'stage_name': 'Weed Control',
                        'days_after_sowing': 35,
                        'brand': 'Syngenta',
                        'active_ingredient': '2,4-D Ethyl Ester',
                        'dose_per_acre': '500 ml/acre',
                        'purpose': 'Broad leaf weed control'
                    },
                    {
                        'stage_name': 'Second Fertilizer Application',
                        'days_after_sowing': 45,
                        'brand': 'IFFCO',
                        'active_ingredient': 'NPK 12:32:16',
                        'dose_per_acre': '25 kg/acre',
                        'purpose': 'Boost flowering and grain formation'
                    },
                    {
                        'stage_name': 'Disease Management',
                        'days_after_sowing': 60,
                        'brand': 'BASF',
                        'active_ingredient': 'Propiconazole',
                        'dose_per_acre': '200 ml/acre',
                        'purpose': 'Control of rust and other fungal diseases'
                    }
                ]
            },
            {
                'name': 'Rice',
                'variety': 'Pusa Basmati 1121',
                'season': 'Kharif',
                'remarks': 'Premium basmati variety with excellent grain quality',
                'stages': [
                    {
                        'stage_name': 'Nursery Preparation',
                        'days_after_sowing': 0,
                        'brand': 'Dhanuka',
                        'active_ingredient': 'Carbendazim',
                        'dose_per_acre': '1 gm/kg seed',
                        'purpose': 'Seed treatment for healthy seedlings'
                    },
                    {
                        'stage_name': 'Transplanting',
                        'days_after_sowing': 25,
                        'brand': 'Coromandel',
                        'active_ingredient': 'DAP',
                        'dose_per_acre': '25 kg/acre',
                        'purpose': 'Initial phosphorus supply for root development'
                    },
                    {
                        'stage_name': 'Tillering Stage',
                        'days_after_sowing': 40,
                        'brand': 'Rallis',
                        'active_ingredient': 'Butachlor',
                        'dose_per_acre': '1.5 liter/acre',
                        'purpose': 'Pre-emergence herbicide for weed control'
                    },
                    {
                        'stage_name': 'Panicle Initiation',
                        'days_after_sowing': 65,
                        'brand': 'Tata Chemicals',
                        'active_ingredient': 'Urea',
                        'dose_per_acre': '40 kg/acre',
                        'purpose': 'Nitrogen boost for panicle development'
                    },
                    {
                        'stage_name': 'Flowering Stage',
                        'days_after_sowing': 85,
                        'brand': 'FMC',
                        'active_ingredient': 'Tricyclazole',
                        'dose_per_acre': '300 gm/acre',
                        'purpose': 'Blast disease control during flowering'
                    }
                ]
            },
            {
                'name': 'Cotton',
                'variety': 'Bt Cotton Hybrid',
                'season': 'Kharif',
                'remarks': 'Bollworm resistant variety with high fiber quality',
                'stages': [
                    {
                        'stage_name': 'Seed Treatment',
                        'days_after_sowing': 0,
                        'brand': 'Monsanto',
                        'active_ingredient': 'Imidacloprid',
                        'dose_per_acre': '5 ml/kg seed',
                        'purpose': 'Protection against sucking pests'
                    },
                    {
                        'stage_name': 'Germination Support',
                        'days_after_sowing': 15,
                        'brand': 'Godrej Agrovet',
                        'active_ingredient': 'Phosphorus Solubilizing Bacteria',
                        'dose_per_acre': '2 kg/acre',
                        'purpose': 'Enhanced nutrient uptake and root development'
                    },
                    {
                        'stage_name': 'Squaring Stage',
                        'days_after_sowing': 45,
                        'brand': 'Dow AgroSciences',
                        'active_ingredient': 'Acetamiprid',
                        'dose_per_acre': '100 gm/acre',
                        'purpose': 'Control of aphids and jassids'
                    },
                    {
                        'stage_name': 'Flowering Stage',
                        'days_after_sowing': 70,
                        'brand': 'Adama',
                        'active_ingredient': 'Emamectin Benzoate',
                        'dose_per_acre': '200 gm/acre',
                        'purpose': 'American bollworm control'
                    },
                    {
                        'stage_name': 'Boll Development',
                        'days_after_sowing': 95,
                        'brand': 'Crystal Crop Protection',
                        'active_ingredient': 'Potassium Nitrate',
                        'dose_per_acre': '5 kg/acre',
                        'purpose': 'Improve boll weight and fiber quality'
                    }
                ]
            }
        ]
        
        created_count = 0
        
        for crop_data in crops_data:
            stages_data = crop_data.pop('stages')
            
            # Create or get crop
            crop, created = Crop.objects.get_or_create(
                name=crop_data['name'],
                variety=crop_data['variety'],
                defaults={
                    'season': crop_data['season'],
                    'remarks': crop_data['remarks'],
                    'created_by': user
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created crop: {crop.name} - {crop.variety}')
                
                # Create stages for the crop
                for stage_data in stages_data:
                    stage = CropStage.objects.create(
                        crop=crop,
                        **stage_data
                    )
                    self.stdout.write(f'  - Created stage: {stage.stage_name} (DAS: {stage.days_after_sowing})')
            else:
                self.stdout.write(f'Crop already exists: {crop.name} - {crop.variety}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} crops with their stages!')
        )
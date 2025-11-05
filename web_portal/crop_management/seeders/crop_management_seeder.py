from crop_management.models import Crop, CropVariety, YieldData, FarmingPractice
from farm.models import Farm
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()

class CropManagementSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def create_crops(self, users):
        """Create sample crops"""
        crops_data = [
            {
                'name': 'Wheat',
                'category': 'cereal',
                'growth_season': 'rabi',
                'growth_cycle_days': 120,
                'description': 'Major cereal crop',
                'water_requirement': 'medium'
            },
            {
                'name': 'Rice',
                'category': 'cereal',
                'growth_season': 'kharif',
                'growth_cycle_days': 150,
                'description': 'Staple food crop',
                'water_requirement': 'high'
            },
            {
                'name': 'Cotton',
                'category': 'fiber',
                'growth_season': 'kharif',
                'growth_cycle_days': 180,
                'description': 'Cash crop for fiber',
                'water_requirement': 'medium'
            },
            {
                'name': 'Sugarcane',
                'category': 'other',
                'growth_season': 'perennial',
                'growth_cycle_days': 365,
                'description': 'Sugar producing crop',
                'water_requirement': 'high'
            },
            {
                'name': 'Tomato',
                'category': 'vegetable',
                'growth_season': 'rabi',
                'growth_cycle_days': 90,
                'description': 'Popular vegetable crop',
                'water_requirement': 'medium'
            }
        ]
        
        crops = []
        for i, crop_data in enumerate(crops_data, 1):
            crop, created = Crop.objects.get_or_create(
                name=crop_data['name'],
                defaults={
                    'category': crop_data['category'],
                    'growth_season': crop_data['growth_season'],
                    'growth_cycle_days': crop_data['growth_cycle_days'],
                    'description': crop_data['description'],
                    'water_requirement': crop_data['water_requirement'],
                    'created_by': users[0] if users else None
                }
            )
            crops.append(crop)
            if self.stdout:
                if created:
                    self.stdout.write(f'Created crop: {crop.name}')
                else:
                    self.stdout.write(f'Crop already exists: {crop.name}')
        return crops

    def create_crop_varieties(self, users):
        """Create sample crop varieties"""
        crops = list(Crop.objects.all()[:5])
        varieties = []
        
        variety_data = [
            {'name': 'Wheat-9', 'code': 'WHT-9', 'yield': 25, 'days': 85},
            {'name': 'Basmati-385', 'code': 'BSM-385', 'yield': 30, 'days': 90},
            {'name': 'Cotton-BT', 'code': 'CTN-BT', 'yield': 35, 'days': 95},
            {'name': 'Sugarcane-CP', 'code': 'SGC-CP', 'yield': 40, 'days': 100},
            {'name': 'Roma-Tomato', 'code': 'TOM-ROM', 'yield': 45, 'days': 105}
        ]
        
        for i in range(min(5, len(crops))):
            variety, created = CropVariety.objects.get_or_create(
                variety_code=variety_data[i]['code'],
                defaults={
                    'crop': crops[i],
                    'name': variety_data[i]['name'],
                    'description': f'High-yield variety of {crops[i].name}',
                    'yield_potential': Decimal(str(variety_data[i]['yield'])),
                    'maturity_days': variety_data[i]['days'],
                    'disease_resistance': f'Resistant to common {crops[i].name} diseases',
                    'recommended_regions': 'Punjab, Sindh, KPK',
                }
            )
            varieties.append(variety)
            if self.stdout:
                if created:
                    self.stdout.write(f'Created crop variety: {variety.name}')
                else:
                    self.stdout.write(f'Crop variety already exists: {variety.name}')
        return varieties

    def create_yield_data(self, users):
        """Create sample yield data"""
        crops = list(Crop.objects.all()[:5])
        farms = list(Farm.objects.all()[:5])
        yield_data = []
        
        seasons = ['kharif', 'rabi', 'zaid', 'kharif', 'rabi']
        
        for i in range(min(5, len(crops), len(farms))):
            data, created = YieldData.objects.get_or_create(
                crop=crops[i],
                farm=farms[i],
                harvest_year=2024,
                harvest_season=seasons[i],
                defaults={
                    'area_cultivated': Decimal(f'{5 + i*2}'),
                    'total_yield': Decimal(f'{100 + i*50}'),
                    'yield_per_hectare': Decimal(f'{15 + i*3}'),
                    'quality_grade': 'A' if i < 2 else 'B' if i < 4 else 'C',
                    'market_price': Decimal(f'{50 + i*10}'),
                    'input_cost': Decimal(f'{30 + i*5}'),
                    'notes': f'Yield data for {crops[i].name} in {seasons[i]} season',
                    'recorded_by': users[0] if users else None
                }
            )
            yield_data.append(data)
            if self.stdout:
                if created:
                    self.stdout.write(f'Created yield data: {crops[i].name} - {seasons[i]} 2024')
                else:
                    self.stdout.write(f'Yield data already exists: {crops[i].name} - {seasons[i]} 2024')
        return yield_data

    def create_farming_practices(self, users):
        """Create sample farming practices"""
        crops = list(Crop.objects.all()[:5])
        practices = []
        practice_types = ['irrigation', 'fertilization', 'pest_control', 'harvesting', 'soil_preparation']
        practice_titles = ['Irrigation Management', 'Fertilizer Application', 'Pest Control', 'Harvesting Techniques', 'Soil Preparation']
        
        for i in range(1, 6):
            if i <= len(crops):
                practice, created = FarmingPractice.objects.get_or_create(
                    title=practice_titles[i-1],
                    crop=crops[i-1],
                    practice_type=practice_types[i-1],
                    defaults={
                        'description': f'Detailed description for {practice_titles[i-1]}',
                        'implementation_steps': f'Step-by-step implementation for {practice_titles[i-1]}',
                        'timing_description': f'Timing description for {practice_titles[i-1]}',
                        'required_materials': f'Materials needed for {practice_titles[i-1]}',
                        'expected_impact': f'Expected impact from {practice_titles[i-1]}',
                        'labor_requirement': 'medium',
                        'estimated_cost': Decimal(f'{100 + i*20}'),
                        'created_by': users[0] if users else None
                    }
                )
                practices.append(practice)
        if self.stdout:
            self.stdout.write(f'Created {len(practices)} farming practices')
        return practices
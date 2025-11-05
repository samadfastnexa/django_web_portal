from decimal import Decimal
from farmers.models import Farmer, FarmingHistory

class FarmersSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def log(self, message):
        if self.stdout:
            self.stdout.write(message)
    
    def create_farmers(self):
        """Create sample farmers"""
        farmers = []
        for i in range(1, 6):
            farmer, created = Farmer.objects.get_or_create(
                farmer_id=f'FRM{i:04d}',
                defaults={
                    'first_name': f'Farmer',
                    'last_name': f'{i}',
                    'name': f'Farmer {i}',
                    'father_name': f'Father {i}',
                    'gender': 'male',
                    'cnic': f'12345-678901{i}-{i}',
                    'primary_phone': f'+92300123456{i}',
                    'email': f'farmer{i}@example.com',
                    'address': f'Village {i}, District {i}',
                    'village': f'Village {i}',
                    'tehsil': f'Tehsil {i}',
                    'district': f'District {i}',
                    'province': 'Punjab',
                    'education_level': 'primary',
                    'total_land_area': Decimal(f'{i}.50'),
                }
            )
            farmers.append(farmer)
        self.log(f'Created {len(farmers)} farmers')
        return farmers
    
    def create_farming_histories(self):
        """Create sample farming histories for farmers"""
        farmers = list(Farmer.objects.all()[:5])
        farming_histories = []
        
        crops = ['Wheat', 'Rice', 'Cotton', 'Sugarcane', 'Tomato']
        seasons = ['kharif', 'rabi', 'zaid']
        years = [2022, 2023, 2024]
        
        for i, farmer in enumerate(farmers):
            for year in years:
                for j, season in enumerate(seasons[:2]):  # Only use first 2 seasons
                    crop_name = crops[i % len(crops)]
                    
                    history, created = FarmingHistory.objects.get_or_create(
                        farmer=farmer,
                        year=year,
                        season=season,
                        crop_name=crop_name,
                        defaults={
                            'area_cultivated': Decimal(f'{2 + i}'),
                            'total_yield': Decimal(f'{500 + i*100 + j*50}'),
                            'yield_per_acre': Decimal(f'{200 + i*20}'),
                            'input_cost': Decimal(f'{15000 + i*2000}'),
                            'market_price': Decimal(f'{50 + i*5}'),
                            'total_income': Decimal(f'{25000 + i*5000}'),
                            'profit_loss': Decimal(f'{10000 + i*1000}'),
                            'farming_practices_used': f'Traditional farming methods for {crop_name}',
                            'challenges_faced': f'Weather challenges in {season} season',
                            'notes': f'Farming history for {crop_name} in {season} {year}'
                        }
                    )
                    farming_histories.append(history)
                    
        self.log(f'Created {len(farming_histories)} farming history records')
        return farming_histories
    
    def seed_all(self):
        """Seed all farmers related data"""
        farmers = self.create_farmers()
        farming_histories = self.create_farming_histories()
        
        return {
            'farmers': farmers,
            'farming_histories': farming_histories
        }
from decimal import Decimal
from farm.models import Farm

class FarmSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def log(self, message):
        if self.stdout:
            self.stdout.write(message)
    
    def create_farms(self, users):
        """Create sample farms"""
        farms = []
        soil_types = ['clay', 'sandy', 'silty', 'peaty', 'chalky']
        for i in range(1, 6):
            farm, created = Farm.objects.get_or_create(
                name=f'Farm {i}',
                owner=users[i-1],
                defaults={
                    'address': f'Farm Address {i}',
                    'geolocation': f'33.{i:02d}0000,76.{i:02d}0000',
                    'size': Decimal(f'{10 + i*5}'),
                    'soil_type': soil_types[i-1],
                    'ownership_details': f'Ownership details for Farm {i}',
                }
            )
            farms.append(farm)
        self.log(f'Created {len(farms)} farms')
        return farms
    
    def seed_all(self, users):
        """Seed all farm related data"""
        farms = self.create_farms(users)
        
        return {
            'farms': farms
        }
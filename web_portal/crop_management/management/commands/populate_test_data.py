from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random
from decimal import Decimal

from crop_management.models import Crop, CropVariety, YieldData, FarmingPractice, CropResearch
from farm.models import Farm

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate the database with test data for crop management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before adding new test data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            CropResearch.objects.all().delete()
            FarmingPractice.objects.all().delete()
            YieldData.objects.all().delete()
            CropVariety.objects.all().delete()
            Crop.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Get or create a default user
        try:
            user = User.objects.get(username='admin')
        except User.DoesNotExist:
            try:
                user = User.objects.create_user(
                    username='admin',
                    email='admin@cropmanagement.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User',
                    is_staff=True,
                    is_superuser=True
                )
            except Exception:
                # If admin user creation fails, use the first available superuser
                user = User.objects.filter(is_superuser=True).first()
                if not user:
                    self.stdout.write(self.style.ERROR('No superuser found. Please create one first.'))
                    return

        # Create sample farms if they don't exist
        farms = []
        farm_data = [
            {'name': 'Green Valley Farm', 'address': 'Punjab, Pakistan', 'size': Decimal('50.5'), 'soil_type': 'loamy'},
            {'name': 'Sunrise Agriculture', 'address': 'Sindh, Pakistan', 'size': Decimal('75.2'), 'soil_type': 'clay'},
            {'name': 'Golden Fields', 'address': 'KPK, Pakistan', 'size': Decimal('120.8'), 'soil_type': 'sandy'},
            {'name': 'River Side Farm', 'address': 'Balochistan, Pakistan', 'size': Decimal('95.3'), 'soil_type': 'loamy'},
        ]
        
        for farm_info in farm_data:
            farm, created = Farm.objects.get_or_create(
                name=farm_info['name'],
                defaults={
                    'address': farm_info['address'],
                    'size': farm_info['size'],
                    'soil_type': farm_info['soil_type'],
                    'owner': user,
                    'geolocation': '31.5204,74.3587'
                }
            )
            farms.append(farm)

        self.stdout.write('Creating crops...')
        crops_data = [
            {
                'name': 'Wheat',
                'scientific_name': 'Triticum aestivum',
                'category': 'cereal',
                'growth_season': 'rabi',
                'growth_cycle_days': 120,
                'water_requirement': 'medium',
                'soil_type_preference': 'Well-drained loamy soil',
                'climate_requirement': 'Cool, dry climate during growing season',
                'description': 'Major staple crop grown extensively in Pakistan',
                'nutritional_value': {'protein': '12-15%', 'carbohydrates': '70-75%', 'fiber': '2-3%'},
                'market_availability': 'Year-round',
                'economic_importance': 'Primary food grain and export commodity'
            },
            {
                'name': 'Rice',
                'scientific_name': 'Oryza sativa',
                'category': 'cereal',
                'growth_season': 'kharif',
                'growth_cycle_days': 150,
                'water_requirement': 'high',
                'soil_type_preference': 'Clay loam with good water retention',
                'climate_requirement': 'Hot, humid climate with abundant water',
                'description': 'Second most important cereal crop in Pakistan',
                'nutritional_value': {'protein': '7-8%', 'carbohydrates': '78-80%', 'fiber': '0.5%'},
                'market_availability': 'Post-harvest season',
                'economic_importance': 'Major export crop and food security'
            },
            {
                'name': 'Cotton',
                'scientific_name': 'Gossypium hirsutum',
                'category': 'fiber',
                'growth_season': 'kharif',
                'growth_cycle_days': 180,
                'water_requirement': 'high',
                'soil_type_preference': 'Deep, well-drained fertile soil',
                'climate_requirement': 'Hot climate with moderate rainfall',
                'description': 'White gold of Pakistan, major cash crop',
                'nutritional_value': {},
                'market_availability': 'October to February',
                'economic_importance': 'Backbone of textile industry'
            },
            {
                'name': 'Sugarcane',
                'scientific_name': 'Saccharum officinarum',
                'category': 'other',
                'growth_season': 'perennial',
                'growth_cycle_days': 365,
                'water_requirement': 'high',
                'soil_type_preference': 'Rich, well-drained soil',
                'climate_requirement': 'Tropical and subtropical climate',
                'description': 'Important cash crop for sugar production',
                'nutritional_value': {'sucrose': '12-18%', 'fiber': '12-16%'},
                'market_availability': 'November to April',
                'economic_importance': 'Sugar industry and ethanol production'
            },
            {
                'name': 'Maize',
                'scientific_name': 'Zea mays',
                'category': 'cereal',
                'growth_season': 'kharif',
                'growth_cycle_days': 100,
                'water_requirement': 'medium',
                'soil_type_preference': 'Well-drained fertile soil',
                'climate_requirement': 'Warm climate with adequate rainfall',
                'description': 'Versatile crop used for food, feed, and industry',
                'nutritional_value': {'protein': '9-10%', 'carbohydrates': '74-75%', 'fat': '4-5%'},
                'market_availability': 'Year-round',
                'economic_importance': 'Food security and livestock feed'
            }
        ]

        crops = []
        for crop_data in crops_data:
            crop, created = Crop.objects.get_or_create(
                name=crop_data['name'],
                defaults={**crop_data, 'created_by': user}
            )
            crops.append(crop)
            if created:
                self.stdout.write(f'Created crop: {crop.name}')

        self.stdout.write('Creating crop varieties...')
        varieties_data = [
            # Wheat varieties
            {
                'crop': 'Wheat',
                'name': 'Punjab-2011',
                'variety_code': 'WH-PB-2011',
                'yield_potential': Decimal('4500'),
                'maturity_days': 115,
                'disease_resistance': 'Rust resistant, moderate stripe rust resistance',
                'pest_resistance': 'Aphid tolerant',
                'quality_attributes': {'protein': '12.5%', 'gluten': 'High', 'test_weight': '78 kg/hl'},
                'special_requirements': 'Requires timely irrigation and balanced fertilization',
                'recommended_regions': 'Punjab, Sindh irrigated areas',
                'seed_availability': 'available',
                'description': 'High yielding wheat variety suitable for irrigated conditions',
                'developed_by': 'Punjab Agricultural Research Institute',
                'release_year': 2011
            },
            {
                'crop': 'Wheat',
                'name': 'Sindh-81',
                'variety_code': 'WH-SD-81',
                'yield_potential': Decimal('4200'),
                'maturity_days': 120,
                'disease_resistance': 'Yellow rust resistant',
                'pest_resistance': 'Moderate pest resistance',
                'quality_attributes': {'protein': '11.8%', 'gluten': 'Medium', 'test_weight': '76 kg/hl'},
                'special_requirements': 'Drought tolerant, suitable for rainfed areas',
                'recommended_regions': 'Sindh, Balochistan',
                'seed_availability': 'available',
                'description': 'Drought tolerant wheat variety for arid regions',
                'developed_by': 'Sindh Agricultural University',
                'release_year': 1981
            },
            # Rice varieties
            {
                'crop': 'Rice',
                'name': 'Basmati-385',
                'variety_code': 'RC-BS-385',
                'yield_potential': Decimal('3200'),
                'maturity_days': 145,
                'disease_resistance': 'Blast resistant, bacterial blight tolerant',
                'pest_resistance': 'Brown plant hopper resistant',
                'quality_attributes': {'aroma': 'Strong', 'grain_length': '6.5mm', 'cooking_quality': 'Excellent'},
                'special_requirements': 'Requires puddled soil and standing water',
                'recommended_regions': 'Punjab, Sindh rice belt',
                'seed_availability': 'available',
                'description': 'Premium aromatic rice variety for export',
                'developed_by': 'Rice Research Institute Kala Shah Kaku',
                'release_year': 1985
            },
            {
                'crop': 'Rice',
                'name': 'IRRI-6',
                'variety_code': 'RC-IR-6',
                'yield_potential': Decimal('4500'),
                'maturity_days': 135,
                'disease_resistance': 'Blast tolerant',
                'pest_resistance': 'Stem borer tolerant',
                'quality_attributes': {'grain_type': 'Medium', 'milling_recovery': '68%', 'cooking_quality': 'Good'},
                'special_requirements': 'High water requirement, needs fertile soil',
                'recommended_regions': 'Punjab, Sindh',
                'seed_availability': 'available',
                'description': 'High yielding non-aromatic rice variety',
                'developed_by': 'International Rice Research Institute',
                'release_year': 1975
            },
            # Cotton varieties
            {
                'crop': 'Cotton',
                'name': 'BT-121',
                'variety_code': 'CT-BT-121',
                'yield_potential': Decimal('2800'),
                'maturity_days': 175,
                'disease_resistance': 'Cotton leaf curl virus resistant',
                'pest_resistance': 'Bollworm resistant (Bt gene)',
                'quality_attributes': {'fiber_length': '28-30mm', 'micronaire': '3.5-4.5', 'strength': 'High'},
                'special_requirements': 'Requires warm climate and adequate moisture',
                'recommended_regions': 'Punjab, Sindh cotton belt',
                'seed_availability': 'available',
                'description': 'Bt cotton variety with bollworm resistance',
                'developed_by': 'Central Cotton Research Institute',
                'release_year': 2010
            }
        ]

        varieties = []
        for variety_data in varieties_data:
            crop = next(c for c in crops if c.name == variety_data['crop'])
            variety_data['crop'] = crop
            variety, created = CropVariety.objects.get_or_create(
                name=variety_data['name'],
                crop=crop,
                defaults=variety_data
            )
            varieties.append(variety)
            if created:
                self.stdout.write(f'Created variety: {variety.name}')

        self.stdout.write('Creating yield data...')
        # Generate yield data for the last 3 years
        current_year = timezone.now().year
        for year in range(current_year - 2, current_year + 1):
            for variety in varieties[:8]:  # Use first 8 varieties
                for farm in farms[:3]:  # Use first 3 farms
                    # Determine season based on crop
                    if variety.crop.growth_season == 'rabi':
                        season = 'rabi'
                    elif variety.crop.growth_season == 'kharif':
                        season = 'kharif'
                    else:
                        season = random.choice(['kharif', 'rabi'])
                    
                    # Generate realistic yield data
                    base_yield = float(variety.yield_potential or 3000)
                    variation = random.uniform(0.7, 1.2)  # 70% to 120% of potential
                    yield_per_ha = Decimal(str(round(base_yield * variation, 2)))
                    
                    area = Decimal(str(random.uniform(5, 25)))  # 5-25 hectares
                    total_yield = yield_per_ha * area
                    
                    YieldData.objects.get_or_create(
                        crop=variety.crop,
                        variety=variety,
                        farm=farm,
                        harvest_year=year,
                        harvest_season=season,
                        defaults={
                            'area_cultivated': area,
                            'total_yield': total_yield,
                            'yield_per_hectare': yield_per_ha,
                            'quality_grade': random.choice(['A', 'B', 'C']),
                            'rainfall_mm': Decimal(str(random.uniform(200, 800))),
                            'temperature_avg': Decimal(str(random.uniform(15, 35))),
                            'input_cost': Decimal(str(random.uniform(50000, 150000))),
                            'market_price': Decimal(str(random.uniform(30, 80))),
                            'notes': f'Good harvest in {year} season',
                            'data_source': 'Field Survey',
                            'recorded_by': user
                        }
                    )

        self.stdout.write('Creating farming practices...')
        practices_data = [
            {
                'crop': 'Wheat',
                'title': 'Land Preparation for Wheat',
                'practice_type': 'soil_preparation',
                'description': 'Proper land preparation is crucial for wheat cultivation',
                'implementation_steps': '1. Deep plowing 2. Harrowing 3. Leveling 4. Making irrigation channels',
                'timing_description': 'Start 2-3 weeks before sowing',
                'days_after_planting': None,
                'required_materials': 'Tractor, plow, harrow, leveler',
                'estimated_cost': Decimal('15000'),
                'labor_requirement': 'medium',
                'expected_impact': 'Better seed germination and root development',
                'success_indicators': 'Uniform field surface, good soil structure',
                'applicable_regions': 'All wheat growing areas',
                'climate_suitability': 'Suitable for all climates',
                'research_source': 'Agricultural Extension Department',
                'validation_status': 'proven',
                'priority_level': 'high'
            },
            {
                'crop': 'Rice',
                'title': 'Transplanting Method for Rice',
                'practice_type': 'planting',
                'description': 'Proper transplanting technique for rice seedlings',
                'implementation_steps': '1. Prepare nursery 2. Raise seedlings 3. Prepare main field 4. Transplant at 25-30 days',
                'timing_description': 'Transplant when seedlings are 25-30 days old',
                'days_after_planting': 25,
                'required_materials': 'Healthy seedlings, transplanting tools',
                'estimated_cost': Decimal('25000'),
                'labor_requirement': 'high',
                'expected_impact': 'Higher yield and better plant establishment',
                'success_indicators': 'Good plant stand, minimal transplanting shock',
                'applicable_regions': 'Rice growing areas of Punjab and Sindh',
                'climate_suitability': 'Hot, humid climate',
                'research_source': 'Rice Research Institute',
                'validation_status': 'proven',
                'priority_level': 'high'
            },
            {
                'crop': 'Cotton',
                'title': 'Integrated Pest Management for Cotton',
                'practice_type': 'pest_control',
                'description': 'Comprehensive approach to manage cotton pests',
                'implementation_steps': '1. Monitor pest levels 2. Use beneficial insects 3. Apply selective pesticides 4. Crop rotation',
                'timing_description': 'Throughout the growing season',
                'days_after_planting': 30,
                'required_materials': 'Monitoring tools, beneficial insects, selective pesticides',
                'estimated_cost': Decimal('35000'),
                'labor_requirement': 'medium',
                'expected_impact': 'Reduced pest damage and pesticide use',
                'success_indicators': 'Low pest incidence, healthy beneficial insects',
                'applicable_regions': 'Cotton belt of Punjab and Sindh',
                'climate_suitability': 'Hot, dry climate',
                'research_source': 'Central Cotton Research Institute',
                'validation_status': 'recommended',
                'priority_level': 'high'
            }
        ]

        for practice_data in practices_data:
            crop = next(c for c in crops if c.name == practice_data['crop'])
            practice_data['crop'] = crop
            practice_data['created_by'] = user
            
            practice, created = FarmingPractice.objects.get_or_create(
                title=practice_data['title'],
                crop=crop,
                defaults=practice_data
            )
            if created:
                self.stdout.write(f'Created practice: {practice.title}')

        self.stdout.write('Creating crop research data...')
        research_data = [
            {
                'crop': 'Wheat',
                'title': 'Development of Drought Tolerant Wheat Varieties',
                'research_type': 'climate_adaptation',
                'objective': 'To develop wheat varieties that can withstand water stress conditions',
                'methodology': 'Field trials under controlled drought conditions, molecular marker analysis',
                'findings': 'Identified 5 promising lines with 20% better drought tolerance',
                'conclusions': 'New varieties can maintain yield under 30% reduced irrigation',
                'research_institution': 'National Agricultural Research Centre',
                'principal_investigator': 'Dr. Ahmad Ali',
                'research_period_start': date(2020, 1, 1),
                'research_period_end': date(2023, 12, 31),
                'publication_status': 'published',
                'publication_reference': 'Journal of Arid Agriculture, Vol 15, 2023',
                'doi': '10.1234/jaa.2023.001',
                'practical_applications': 'Varieties suitable for water-scarce regions',
                'impact_assessment': 'Potential to increase wheat production in arid areas by 15%'
            },
            {
                'crop': 'Rice',
                'title': 'Nutrient Management in Basmati Rice',
                'research_type': 'nutrition_study',
                'objective': 'Optimize fertilizer application for maximum yield and quality in Basmati rice',
                'methodology': 'Split plot design with different NPK combinations over 3 seasons',
                'findings': 'Balanced NPK at 120:60:60 kg/ha gave best results',
                'conclusions': 'Proper nutrient management increases yield by 25% and improves grain quality',
                'research_institution': 'Rice Research Institute Kala Shah Kaku',
                'principal_investigator': 'Dr. Fatima Khan',
                'research_period_start': date(2021, 6, 1),
                'research_period_end': date(2023, 5, 31),
                'publication_status': 'peer_reviewed',
                'publication_reference': 'Pakistan Journal of Agricultural Sciences, 2023',
                'doi': '10.1234/pjas.2023.002',
                'practical_applications': 'Fertilizer recommendations for Basmati cultivation',
                'impact_assessment': 'Improved farmer income through better yield and quality'
            },
            {
                'crop': 'Cotton',
                'title': 'Biological Control of Cotton Bollworm',
                'research_type': 'pest_management',
                'objective': 'Evaluate effectiveness of biological agents against cotton bollworm',
                'methodology': 'Field trials using Trichogramma wasps and Bt sprays',
                'findings': 'Biological control reduced bollworm damage by 60%',
                'conclusions': 'Integrated approach with biological agents is highly effective',
                'research_institution': 'Central Cotton Research Institute',
                'principal_investigator': 'Dr. Muhammad Hassan',
                'research_period_start': date(2022, 4, 1),
                'research_period_end': date(2023, 10, 31),
                'publication_status': 'completed',
                'publication_reference': '',
                'doi': '',
                'practical_applications': 'Reduced pesticide use and cost-effective pest control',
                'impact_assessment': 'Environmental benefits and reduced production costs'
            }
        ]

        for research_info in research_data:
            crop = next(c for c in crops if c.name == research_info['crop'])
            research_info['crop'] = crop
            research_info['added_by'] = user
            
            research, created = CropResearch.objects.get_or_create(
                title=research_info['title'],
                crop=crop,
                defaults=research_info
            )
            if created:
                self.stdout.write(f'Created research: {research.title}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated test data:\n'
                f'- {Crop.objects.count()} crops\n'
                f'- {CropVariety.objects.count()} varieties\n'
                f'- {YieldData.objects.count()} yield records\n'
                f'- {FarmingPractice.objects.count()} farming practices\n'
                f'- {CropResearch.objects.count()} research records'
            )
        )
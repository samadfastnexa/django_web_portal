from decimal import Decimal
from datetime import date, timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from FieldAdvisoryService.models import (
    Company, Region, Zone, Territory, Dealer, DealerRequest, 
    MeetingSchedule, SalesOrder, SalesOrderAttachment
)

class FieldAdvisorySeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def log(self, message):
        if self.stdout:
            self.stdout.write(message)
    
    def create_companies(self, users):
        """Create sample companies"""
        companies = []
        for i in range(1, 6):
            company, created = Company.objects.get_or_create(
                Company_name=f'Company {i}',
                defaults={
                    'name': f'Company {i}',
                    'description': f'Description for Company {i}',
                    'address': f'Address {i}, City {i}',
                    'email': f'company{i}@example.com',
                    'contact_number': f'042123456{i}',
                    'latitude': Decimal(f'31.{i:02d}0000'),
                    'longitude': Decimal(f'74.{i:02d}0000'),
                    'created_by': users[i-1],
                }
            )
            companies.append(company)
        self.log(f'Created {len(companies)} companies')
        return companies
    
    def create_regions(self, companies, users):
        """Create sample regions"""
        regions = []
        for i in range(1, 6):
            region, created = Region.objects.get_or_create(
                name=f'Region {i}',
                company=companies[i-1],
                defaults={'created_by': users[i-1]}
            )
            regions.append(region)
        self.log(f'Created {len(regions)} regions')
        return regions
    
    def create_zones(self, companies, regions, users):
        """Create sample zones"""
        zones = []
        for i in range(1, 6):
            zone, created = Zone.objects.get_or_create(
                name=f'Zone {i}',
                company=companies[i-1],
                region=regions[i-1],
                defaults={'created_by': users[i-1]}
            )
            zones.append(zone)
        self.log(f'Created {len(zones)} zones')
        return zones
    
    def create_territories(self, companies, zones, users):
        """Create sample territories"""
        territories = []
        for i in range(1, 6):
            territory, created = Territory.objects.get_or_create(
                name=f'Territory {i}',
                company=companies[i-1],
                zone=zones[i-1],
                defaults={'created_by': users[i-1]}
            )
            territories.append(territory)
        self.log(f'Created {len(territories)} territories')
        return territories
    
    def create_dealers(self, users, companies, regions, zones, territories):
        """Create sample dealers"""
        dealers = []
        for i in range(1, 6):
            # Create a dummy image file
            image_content = b'dummy image content'
            image_file = SimpleUploadedFile(f'test_image_{i}.jpg', image_content, content_type='image/jpeg')
            
            dealer, created = Dealer.objects.get_or_create(
                cnic_number=f'11111-222222{i}-{i}',
                defaults={
                    'user': users[i-1],
                    'card_code': f'CARD{i:03d}',
                    'name': f'Dealer {i}',
                    'contact_number': f'03001111{i:03d}',
                    'company': companies[i-1],
                    'region': regions[i-1],
                    'zone': zones[i-1],
                    'territory': territories[i-1],
                    'address': f'Dealer Address {i}',
                    'latitude': Decimal(f'31.{i:02d}5000'),
                    'longitude': Decimal(f'74.{i:02d}5000'),
                    'created_by': users[i-1],
                    'cnic_front_image': image_file,
                    'cnic_back_image': image_file,
                }
            )
            dealers.append(dealer)
        self.log(f'Created {len(dealers)} dealers')
        return dealers
    
    def create_dealer_requests(self, users, companies, regions, zones, territories):
        """Create sample dealer requests"""
        requests = []
        statuses = ['pending', 'approved', 'rejected', 'pending', 'approved']
        filer_statuses = ['filer', 'non_filer', 'filer', 'non_filer', 'filer']
        
        for i in range(1, 6):
            image_content = b'dummy image content'
            image_file = SimpleUploadedFile(f'dealer_request_{i}.jpg', image_content, content_type='image/jpeg')
            
            request, created = DealerRequest.objects.get_or_create(
                cnic_number=f'99999-888888{i}-{i}',
                defaults={
                    'requested_by': users[i-1],
                    'owner_name': f'Owner {i}',
                    'business_name': f'Business {i}',
                    'contact_number': f'03002222{i:03d}',
                    'address': f'Business Address {i}',
                    'cnic_front': image_file,
                    'cnic_back': image_file,
                    'govt_license_number': f'LIC{i:06d}',
                    'license_expiry': date.today() + timedelta(days=365*i),
                    'reason': f'Reason for dealer request {i}',
                    'status': statuses[i-1],
                    'filer_status': filer_statuses[i-1],
                    'company': companies[i-1],
                    'region': regions[i-1],
                    'zone': zones[i-1],
                    'territory': territories[i-1],
                    'minimum_investment': 500000 + i*100000,
                }
            )
            requests.append(request)
        self.log(f'Created {len(requests)} dealer requests')
        return requests
    
    def create_meeting_schedules(self, users):
        """Create sample meeting schedules"""
        schedules = []
        for i in range(1, 6):
            schedule, created = MeetingSchedule.objects.get_or_create(
                staff=users[i-1],
                date=date.today() + timedelta(days=i*7),
                defaults={
                    'location': f'Meeting Location {i}',
                    'min_farmers_required': 5 + i,
                    'confirmed_attendees': i,
                }
            )
            schedules.append(schedule)
        self.log(f'Created {len(schedules)} meeting schedules')
        return schedules
    
    def create_sales_orders(self, users):
        """Create sample sales orders"""
        # First get meeting schedules and dealers if they exist
        schedules = list(MeetingSchedule.objects.all()[:5])
        dealers = list(Dealer.objects.all()[:5])
        
        if not schedules or not dealers:
            self.log('Skipping sales orders - missing dependencies')
            return []
            
        orders = []
        statuses = ['pending', 'entertained', 'rejected', 'closed', 'pending']
        for i in range(1, 6):
            if i <= len(schedules) and i <= len(dealers):
                order, created = SalesOrder.objects.get_or_create(
                    schedule=schedules[i-1],
                    staff=users[i-1],
                    dealer=dealers[i-1],
                    defaults={'status': statuses[i-1]}
                )
                orders.append(order)
        self.log(f'Created {len(orders)} sales orders')
        return orders
    
    def seed_all(self, users):
        """Seed all FieldAdvisoryService related data"""
        companies = self.create_companies(users)
        regions = self.create_regions(companies, users)
        zones = self.create_zones(companies, regions, users)
        territories = self.create_territories(companies, zones, users)
        dealers = self.create_dealers(users, companies, regions, zones, territories)
        dealer_requests = self.create_dealer_requests(users, companies, regions, zones, territories)
        meeting_schedules = self.create_meeting_schedules(users)
        sales_orders = self.create_sales_orders(users)
        
        return {
            'companies': companies,
            'regions': regions,
            'zones': zones,
            'territories': territories,
            'dealers': dealers,
            'dealer_requests': dealer_requests,
            'meeting_schedules': meeting_schedules,
            'sales_orders': sales_orders
        }
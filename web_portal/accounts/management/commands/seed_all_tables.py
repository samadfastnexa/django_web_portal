import os
import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
import random

# Import all models
from accounts.models import Role, SalesStaffProfile
from farmers.models import Farmer
from farm.models import Farm
from attendance.models import Holiday, Attendance, AttendanceRequest
from complaints.models import Complaint
from FieldAdvisoryService.models import (
    Company, Region, Zone, Territory, Dealer, DealerRequest, 
    MeetingSchedule, SalesOrder, SalesOrderAttachment
)
from farmerMeetingDataEntry.models import (
    Meeting, FarmerAttendance, MeetingAttachment, FieldDay, FieldDayAttendance
)
from preferences.models import Setting
from crop_management.models import Crop, CropVariety, YieldData, FarmingPractice

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed all tables with 5 records each'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting comprehensive seeding...'))
        
        with transaction.atomic():
            # Create users first (needed for foreign keys)
            users = self.create_users()
            
            # Create roles
            roles = self.create_roles()
            
            # Create companies (needed for many other models)
            companies = self.create_companies(users)
            
            # Create regions, zones, territories
            regions = self.create_regions(companies, users)
            zones = self.create_zones(companies, regions, users)
            territories = self.create_territories(companies, zones, users)
            
            # Create other models
            self.create_sales_staff_profiles(users, roles)
            self.create_farmers()
            self.create_farms(users)
            self.create_holidays()
            self.create_attendance(users)
            self.create_attendance_requests(users)
            self.create_complaints(users)
            self.create_dealers(users, companies, regions, zones, territories)
            self.create_dealer_requests(users, companies, regions, zones, territories)
            self.create_meeting_schedules(users)
            self.create_sales_orders(users)
            self.create_meetings(users, regions, zones, territories)
            self.create_field_days(users, regions, zones, territories)
            self.create_settings(users)
            self.create_crops(users)
            self.create_crop_varieties(users)
            self.create_yield_data(users)
            self.create_farming_practices(users)
            
        self.stdout.write(self.style.SUCCESS('Successfully seeded all tables!'))

    def create_users(self):
        users = []
        for i in range(1, 6):
            user, created = User.objects.get_or_create(
                username=f'user{i}',
                defaults={
                    'email': f'user{i}@example.com',
                    'first_name': f'User{i}',
                    'last_name': f'Test{i}',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
        self.stdout.write(f'Created {len(users)} users')
        return users

    def create_roles(self):
        roles = []
        role_names = ['Admin', 'Manager', 'Field Staff', 'Sales Rep', 'Supervisor']
        for i, name in enumerate(role_names, 1):
            role, created = Role.objects.get_or_create(
                name=name
            )
            roles.append(role)
        self.stdout.write(f'Created {len(roles)} roles')
        return roles

    def create_companies(self, users):
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
        self.stdout.write(f'Created {len(companies)} companies')
        return companies

    def create_regions(self, companies, users):
        regions = []
        for i in range(1, 6):
            region, created = Region.objects.get_or_create(
                name=f'Region {i}',
                company=companies[i-1],
                defaults={'created_by': users[i-1]}
            )
            regions.append(region)
        self.stdout.write(f'Created {len(regions)} regions')
        return regions

    def create_zones(self, companies, regions, users):
        zones = []
        for i in range(1, 6):
            zone, created = Zone.objects.get_or_create(
                name=f'Zone {i}',
                company=companies[i-1],
                region=regions[i-1],
                defaults={'created_by': users[i-1]}
            )
            zones.append(zone)
        self.stdout.write(f'Created {len(zones)} zones')
        return zones

    def create_territories(self, companies, zones, users):
        territories = []
        for i in range(1, 6):
            territory, created = Territory.objects.get_or_create(
                name=f'Territory {i}',
                company=companies[i-1],
                zone=zones[i-1],
                defaults={'created_by': users[i-1]}
            )
            territories.append(territory)
        self.stdout.write(f'Created {len(territories)} territories')
        return territories

    def create_sales_staff_profiles(self, users, roles):
        profiles = []
        designations = ['CEO', 'NSM', 'CEO', 'NSM', 'CEO']  # Use only CEO/NSM to avoid geo validation
        for i in range(1, 6):
            # Assign role to user first
            users[i-1].role = roles[i-1]
            users[i-1].is_sales_staff = True
            users[i-1].save()
            
            profile, created = SalesStaffProfile.objects.get_or_create(
                user=users[i-1],
                defaults={
                    'employee_code': f'EMP{i:03d}',
                    'phone_number': f'03001234{i:03d}',
                    'address': f'Address {i}, City {i}',
                    'designation': designations[i-1],
                    'sick_leave_quota': 10,
                    'casual_leave_quota': 15,
                    'others_leave_quota': 5,
                }
            )
            profiles.append(profile)
        self.stdout.write(f'Created {len(profiles)} sales staff profiles')
        return profiles

    def create_farmers(self):
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
                    'national_id': f'12345-678901{i}-{i}',
                    'primary_phone': f'+92300123456{i}',
                    'email': f'farmer{i}@example.com',
                    'address': f'Village {i}, District {i}',
                    'village': f'Village {i}',
                    'tehsil': f'Tehsil {i}',
                    'district': f'District {i}',
                    'province': 'Punjab',
                    'education_level': 'primary',
                    'total_land_area': Decimal(f'{i}.50'),
                    'cultivated_area': Decimal(f'{i}.00'),
                    'farm_ownership_type': 'owned',
                    'farming_experience': 'intermediate',
                    'years_of_farming': 5 + i,
                    'main_crops_grown': f'Wheat, Rice, Corn',
                    'current_latitude': Decimal(f'32.{i:02d}0000'),
                    'current_longitude': Decimal(f'75.{i:02d}0000'),
                    'farm_latitude': Decimal(f'32.{i:02d}5000'),
                    'farm_longitude': Decimal(f'75.{i:02d}5000'),
                }
            )
            farmers.append(farmer)
        self.stdout.write(f'Created {len(farmers)} farmers')
        return farmers

    def create_farms(self, users):
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
        self.stdout.write(f'Created {len(farms)} farms')
        return farms

    def create_holidays(self):
        holidays = []
        holiday_dates = [
            (date(2024, 1, 1), 'New Year'),
            (date(2024, 3, 23), 'Pakistan Day'),
            (date(2024, 8, 14), 'Independence Day'),
            (date(2024, 11, 9), 'Iqbal Day'),
            (date(2024, 12, 25), 'Quaid-e-Azam Birthday'),
        ]
        
        for holiday_date, holiday_name in holiday_dates:
            holiday, created = Holiday.objects.get_or_create(
                date=holiday_date,
                defaults={
                    'name': holiday_name,
                }
            )
            holidays.append(holiday)
        self.stdout.write(f'Created {len(holidays)} holidays')
        return holidays

    def create_attendance(self, users):
        from datetime import datetime, time
        attendances = []
        for i in range(1, 6):
            attendance_date = date.today() - timedelta(days=i)
            check_in_datetime = timezone.make_aware(datetime.combine(attendance_date, time(9, 0)))
            check_out_datetime = timezone.make_aware(datetime.combine(attendance_date, time(17, 0)))
            
            attendance, created = Attendance.objects.get_or_create(
                user=users[0],  # First user marks attendance
                attendee=users[i-1],  # For different attendees
                check_in_time=check_in_datetime,
                defaults={
                    'check_out_time': check_out_datetime,
                    'latitude': Decimal(f'31.{i:02d}0000'),
                    'longitude': Decimal(f'74.{i:02d}0000'),
                    'source': 'manual',
                }
            )
            attendances.append(attendance)
        self.stdout.write(f'Created {len(attendances)} attendance records')
        return attendances

    def create_attendance_requests(self, users):
        requests = []
        check_types = ['check_in', 'check_out', 'check_in', 'check_out', 'check_in']
        for i in range(1, 6):
            request, created = AttendanceRequest.objects.get_or_create(
                user=users[i-1],
                check_type=check_types[i-1],
                defaults={
                    'reason': f'Request {i} reason',
                    'status': 'pending',
                    'check_in_time': timezone.now() - timedelta(hours=i),
                }
            )
            requests.append(request)
        self.stdout.write(f'Created {len(requests)} attendance requests')
        return requests

    def create_complaints(self, users):
        complaints = []
        statuses = ['open', 'in_progress', 'resolved', 'closed', 'pending']
        for i in range(1, 6):
            complaint, created = Complaint.objects.get_or_create(
                complaint_id=f'COMP{i:04d}',
                user=users[i-1],
                defaults={
                    'message': f'Complaint message {i} - This is a test complaint.',
                    'status': statuses[i-1],
                }
            )
            complaints.append(complaint)
        self.stdout.write(f'Created {len(complaints)} complaints')
        return complaints

    def create_dealers(self, users, companies, regions, zones, territories):
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
        self.stdout.write(f'Created {len(dealers)} dealers')
        return dealers

    def create_dealer_requests(self, users, companies, regions, zones, territories):
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
        self.stdout.write(f'Created {len(requests)} dealer requests')
        return requests

    def create_meeting_schedules(self, users):
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
        self.stdout.write(f'Created {len(schedules)} meeting schedules')
        return schedules

    def create_sales_orders(self, users):
        # First create meeting schedules and dealers if they don't exist
        schedules = list(MeetingSchedule.objects.all()[:5])
        dealers = list(Dealer.objects.all()[:5])
        
        if not schedules or not dealers:
            self.stdout.write('Skipping sales orders - missing dependencies')
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
        self.stdout.write(f'Created {len(orders)} sales orders')
        return orders

    def create_meetings(self, users, regions, zones, territories):
        meetings = []
        for i in range(1, 6):
            meeting, created = Meeting.objects.get_or_create(
                fsm_name=f'FSM {i}',
                date=date.today() + timedelta(days=i*3),
                defaults={
                    'territory': f'Territory {i}',
                    'zone': f'Zone {i}',
                    'region': f'Region {i}',
                    'region_fk': regions[i-1],
                    'zone_fk': zones[i-1],
                    'territory_fk': territories[i-1],
                    'location': f'Meeting Location {i}',
                    'total_attendees': 10 + i,
                    'key_topics_discussed': f'Topics discussed in meeting {i}',
                    'presence_of_zm_rsm': i % 2 == 0,
                    'feedback_from_attendees': f'Feedback from meeting {i}',
                    'suggestions_for_future': f'Suggestions for meeting {i}',
                    'user_id': users[i-1],
                }
            )
            meetings.append(meeting)
        self.stdout.write(f'Created {len(meetings)} meetings')
        return meetings

    def create_field_days(self, users, regions, zones, territories):
        field_days = []
        statuses = ['draft', 'scheduled', 'completed', 'draft', 'scheduled']
        for i in range(1, 6):
            field_day, created = FieldDay.objects.get_or_create(
                title=f'Field Day {i}',
                defaults={
                    'territory': f'Territory {i}',
                    'zone': f'Zone {i}',
                    'region': f'Region {i}',
                    'region_fk': regions[i-1],
                    'zone_fk': zones[i-1],
                    'territory_fk': territories[i-1],
                    'date': date.today() + timedelta(days=i*5),
                    'location': f'Field Day Location {i}',
                    'objectives': f'Objectives for field day {i}',
                    'remarks': f'Remarks for field day {i}',
                    'status': statuses[i-1],
                    'user': users[i-1],
                }
            )
            field_days.append(field_day)
        self.stdout.write(f'Created {len(field_days)} field days')
        return field_days

    def create_settings(self, users):
        settings = []
        for i in range(1, 6):
            setting, created = Setting.objects.get_or_create(
                slug=f'setting_{i}',
                defaults={
                    'user': users[i-1] if i > 1 else None,  # First setting is global
                    'value': {
                        'theme': f'theme_{i}',
                        'language': 'en',
                        'notifications': True,
                        'setting_value': f'value_{i}'
                    }
                }
            )
            settings.append(setting)
        self.stdout.write(f'Created {len(settings)} settings')
        return settings

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
        
        from crop_management.models import Crop
        
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
            if created:
                self.stdout.write(f'Created crop: {crop.name}')
            else:
                self.stdout.write(f'Crop already exists: {crop.name}')

    def create_crop_varieties(self, users):
        from crop_management.models import CropVariety
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
            if created:
                self.stdout.write(f'Created crop variety: {variety.name}')
            else:
                self.stdout.write(f'Crop variety already exists: {variety.name}')
        return varieties

    def create_yield_data(self, users):
        from crop_management.models import YieldData
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
            if created:
                self.stdout.write(f'Created yield data: {crops[i].name} - {seasons[i]} 2024')
            else:
                self.stdout.write(f'Yield data already exists: {crops[i].name} - {seasons[i]} 2024')
        return yield_data

    def create_farming_practices(self, users):
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
        self.stdout.write(f'Created {len(practices)} farming practices')
        return practices
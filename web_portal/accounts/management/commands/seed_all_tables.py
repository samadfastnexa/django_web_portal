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

# Import seeding modules
from accounts.seeders.accounts_seeder import AccountsSeeder
from farmers.seeders.farmers_seeder import FarmersSeeder
from farm.seeders.farm_seeder import FarmSeeder
from attendance.seeders.attendance_seeder import AttendanceSeeder
from complaints.seeders.complaints_seeder import ComplaintsSeeder
from FieldAdvisoryService.seeders.field_advisory_seeder import FieldAdvisorySeeder
from farmerMeetingDataEntry.seeders.farmer_meeting_seeder import FarmerMeetingSeeder
from preferences.seeders.preferences_seeder import PreferencesSeeder
from crop_management.seeders.crop_management_seeder import CropManagementSeeder

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed all tables with 5 records each'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting comprehensive seeding...'))
        
        with transaction.atomic():
            # Initialize seeders
            accounts_seeder = AccountsSeeder(self.stdout)
            farmers_seeder = FarmersSeeder(self.stdout)
            farm_seeder = FarmSeeder(self.stdout)
            attendance_seeder = AttendanceSeeder(self.stdout)
            complaints_seeder = ComplaintsSeeder(self.stdout)
            field_advisory_seeder = FieldAdvisorySeeder(self.stdout)
            farmer_meeting_seeder = FarmerMeetingSeeder(self.stdout)
            preferences_seeder = PreferencesSeeder(self.stdout)
            crop_management_seeder = CropManagementSeeder(self.stdout)
            
            # Create users first (needed for foreign keys)
            users = accounts_seeder.create_users()
            
            # Create roles
            roles = accounts_seeder.create_roles()
            
            # Create companies (needed for many other models)
            companies = field_advisory_seeder.create_companies(users)
            
            # Create regions, zones, territories
            regions = field_advisory_seeder.create_regions(companies, users)
            zones = field_advisory_seeder.create_zones(companies, regions, users)
            territories = field_advisory_seeder.create_territories(companies, zones, users)
            
            # Create other models
            accounts_seeder.create_sales_staff_profiles(users, roles)
            farmers_seeder.create_farmers()
            farm_seeder.create_farms(users)
            attendance_seeder.create_holidays()
            attendance_seeder.create_attendance(users)
            attendance_seeder.create_attendance_requests(users)
            complaints_seeder.create_complaints(users)
            field_advisory_seeder.create_dealers(users, companies, regions, zones, territories)
            field_advisory_seeder.create_dealer_requests(users, companies, regions, zones, territories)
            field_advisory_seeder.create_meeting_schedules(users)
            field_advisory_seeder.create_sales_orders(users)
            farmer_meeting_seeder.create_meetings(users, regions, zones, territories, companies)
            farmer_meeting_seeder.create_field_days(users, regions, zones, territories, companies)
            preferences_seeder.create_settings(users)
            crop_management_seeder.create_crops(users)
            crop_management_seeder.create_crop_varieties(users)
            crop_management_seeder.create_yield_data(users)
            crop_management_seeder.create_farming_practices(users)
            farmers_seeder.create_farming_histories()
            
        self.stdout.write(self.style.SUCCESS('Successfully seeded all tables!'))
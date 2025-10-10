from farmerMeetingDataEntry.models import Meeting, FieldDay, FieldDayAttendance
from farmers.models import Farmer
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from decimal import Decimal
import random

User = get_user_model()

class FarmerMeetingSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def create_meetings(self, users, regions, zones, territories, companies):
        """Create sample meetings"""
        meetings = []
        for i in range(1, 6):
            meeting, created = Meeting.objects.get_or_create(
                fsm_name=f'FSM {i}',
                date=date.today() + timedelta(days=i*3),
                defaults={
                    'company_fk': companies[i-1],
                    'region_fk': regions[i-1],
                    'zone_fk': zones[i-1],
                    'territory_fk': territories[i-1],
                    'location': f'Meeting Location {i}',
                    'total_attendees': 10 + i,
                    'key_topics_discussed': f'Topics discussed in meeting {i}',
                    'presence_of_zm': i % 3 == 0,  # ZM present every 3rd meeting
                    'presence_of_rsm': i % 2 == 0,  # RSM present every 2nd meeting
                    'feedback_from_attendees': f'Feedback from meeting {i}',
                    'suggestions_for_future': f'Suggestions for meeting {i}',
                    'user_id': users[i-1],
                }
            )
            meetings.append(meeting)
        if self.stdout:
            self.stdout.write(f'Created {len(meetings)} meetings')
        return meetings

    def create_field_days(self, users, regions, zones, territories, companies):
        """Create sample field days"""
        field_days = []
        fsm_names = ['Ahmed Hassan', 'Fatima Ali', 'Muhammad Khan', 'Sara Ahmed', 'Ali Raza']
        for i in range(1, 6):
            field_day, created = FieldDay.objects.get_or_create(
                title=fsm_names[i-1],
                defaults={
                    'company_fk': companies[i-1],
                    'region_fk': regions[i-1],
                    'zone_fk': zones[i-1],
                    'territory_fk': territories[i-1],
                    'date': date.today() + timedelta(days=i*5),
                    'location': f'Field Day Location {i}',
                    'total_participants': (i * 5) + 10,  # Sample participant counts: 15, 20, 25, 30, 35
                    'demonstrations_conducted': i * 2,
                    'feedback': f'Positive feedback received from farmers at field day {i}. They appreciated the practical demonstrations and found them very helpful.',
                    'user': users[i-1],
                }
            )
            field_days.append(field_day)
        if self.stdout:
            self.stdout.write(f'Created {len(field_days)} field days')
        
        # Create attendance records for each field day
        self.create_field_day_attendance(field_days)
        
        return field_days
    
    def create_field_day_attendance(self, field_days):
        """Create sample field day attendance records with farmer relationships"""
        farmers = list(Farmer.objects.all())
        if not farmers:
            if self.stdout:
                self.stdout.write('No farmers found. Skipping field day attendance creation.')
            return []
        
        attendance_records = []
        crops = ['Wheat', 'Rice', 'Cotton', 'Sugarcane', 'Tomato', 'Maize', 'Barley', 'Millet']
        
        for field_day in field_days:
            # Create 2-4 attendance records per field day
            num_attendees = random.randint(2, min(4, len(farmers)))
            selected_farmers = random.sample(farmers, num_attendees)
            
            for farmer in selected_farmers:
                # Check if attendance record already exists
                attendance, created = FieldDayAttendance.objects.get_or_create(
                    field_day=field_day,
                    farmer=farmer,
                    defaults={
                        'farmer_name': f'{farmer.first_name} {farmer.last_name}',
                        'contact_number': farmer.primary_phone,
                        'acreage': Decimal(str(random.uniform(1.0, 10.0))),  # Random acreage between 1-10
                        'crop': random.choice(crops),
                    }
                )
                if created:
                    attendance_records.append(attendance)
        
        if self.stdout:
            self.stdout.write(f'Created {len(attendance_records)} field day attendance records')
        return attendance_records
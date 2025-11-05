from decimal import Decimal
from datetime import date, datetime, time, timedelta
from django.utils import timezone
from attendance.models import Holiday, Attendance, AttendanceRequest

class AttendanceSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def log(self, message):
        if self.stdout:
            self.stdout.write(message)
    
    def create_holidays(self):
        """Create sample holidays"""
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
        self.log(f'Created {len(holidays)} holidays')
        return holidays
    
    def create_attendance(self, users):
        """Create sample attendance records"""
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
                    'check_in_latitude': Decimal(f'31.{i:02d}0000'),
                    'check_in_longitude': Decimal(f'74.{i:02d}0000'),
                    'check_out_latitude': Decimal(f'31.{i:02d}0000'),
                    'check_out_longitude': Decimal(f'74.{i:02d}0000'),
                    'source': 'manual',
                }
            )
            attendances.append(attendance)
        self.log(f'Created {len(attendances)} attendance records')
        return attendances
    
    def create_attendance_requests(self, users):
        """Create sample attendance requests"""
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
        self.log(f'Created {len(requests)} attendance requests')
        return requests
    
    def seed_all(self, users):
        """Seed all attendance related data"""
        holidays = self.create_holidays()
        attendances = self.create_attendance(users)
        attendance_requests = self.create_attendance_requests(users)
        
        return {
            'holidays': holidays,
            'attendances': attendances,
            'attendance_requests': attendance_requests
        }
from farmerMeetingDataEntry.models import Meeting, FieldDay
from datetime import date, timedelta
from django.contrib.auth import get_user_model

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
                    'presence_of_zm_rsm': i % 2 == 0,
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
        statuses = ['draft', 'scheduled', 'completed', 'draft', 'scheduled']
        for i in range(1, 6):
            field_day, created = FieldDay.objects.get_or_create(
                title=f'Field Day {i}',
                defaults={
                    'company_fk': companies[i-1],
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
        if self.stdout:
            self.stdout.write(f'Created {len(field_days)} field days')
        return field_days
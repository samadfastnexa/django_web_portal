from complaints.models import Complaint
from django.contrib.auth import get_user_model

User = get_user_model()

class ComplaintsSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def create_complaints(self, users):
        """Create sample complaints"""
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
        if self.stdout:
            self.stdout.write(f'Created {len(complaints)} complaints')
        return complaints
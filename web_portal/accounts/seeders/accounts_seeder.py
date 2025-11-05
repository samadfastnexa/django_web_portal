from django.contrib.auth import get_user_model
from accounts.models import Role, SalesStaffProfile

User = get_user_model()

class AccountsSeeder:
    def __init__(self, stdout=None):
        self.stdout = stdout
    
    def log(self, message):
        if self.stdout:
            self.stdout.write(message)
    
    def create_users(self):
        """Create sample users"""
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
        self.log(f'Created {len(users)} users')
        return users
    
    def create_roles(self):
        """Create sample roles"""
        roles = []
        role_names = ['Admin', 'Manager', 'Field Staff', 'Sales Rep', 'Supervisor']
        for i, name in enumerate(role_names, 1):
            role, created = Role.objects.get_or_create(
                name=name
            )
            roles.append(role)
        self.log(f'Created {len(roles)} roles')
        return roles
    
    def create_sales_staff_profiles(self, users, roles):
        """Create sample sales staff profiles"""
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
        self.log(f'Created {len(profiles)} sales staff profiles')
        return profiles
    
    def seed_all(self):
        """Seed all accounts related data"""
        users = self.create_users()
        roles = self.create_roles()
        profiles = self.create_sales_staff_profiles(users, roles)
        
        return {
            'users': users,
            'roles': roles,
            'profiles': profiles
        }
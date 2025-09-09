# File: accounts/management/commands/seed.py
# Usage: python manage.py seed

# 🚀 Starting database seeding...
# ============================================================

# 📝 Step 1: Creating Admin role
# ✓ Created 'Admin' role
# ✓ Assigned 36 permissions to Admin role

# 📝 Step 2: Creating FirstRole
# ✓ Created 'FirstRole' role
# ✓ Assigned 2 basic permissions to FirstRole
#    FirstRole permissions:
#    - Can view user
#    - Can change user

# 📝 Step 3: Creating superuser
# ✓ Superuser created successfully!
#    Email: admin@example.com
#    Username: adminuser
#    Name: Super Admin
#    Role: Admin
#    Profile Image: No

# 🎯 SEEDING SUMMARY
# ============================================================

# 📋 ROLES (2 total):
#    • Admin: 36 permissions, 1 users
#    • FirstRole: 2 permissions, 0 users

# 👥 USERS (1 total):
#    • Total users: 1
#    • Admin users: 1
#    • Active users: 1

# 🔧 SYSTEM STATUS:
#    • Admin role: ✓ Ready
#    • FirstRole: ✓ Ready
#    • Ready for user registration: ✓ Yes

# 🎉 Database seeding completed successfully!

# 🔑 LOGIN CREDENTIALS:
#    URL: /admin/ or your login page
#    Email: admin@example.com
#    Password: admin123456

# File: accounts/management/commands/seed.py
# Usage: python manage.py seed

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from accounts.models import Role
from django.core.files.uploadedfile import SimpleUploadedFile
import io

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Role
import io

class Command(BaseCommand):
    help = 'Seed the database with Admin and FirstRole, and create a default superuser'

    def add_arguments(self, parser):
        """
        Define optional command-line arguments with default values.
        """
        parser.add_argument('--email', type=str, default='superuser@gmail.com', help='Admin email')
        parser.add_argument('--password', type=str, default='123456789', help='Admin password')
        parser.add_argument('--username', type=str, default='superadmin', help='Admin username')
        parser.add_argument('--first-name', type=str, default='Super', help='Admin first name')
        parser.add_argument('--last-name', type=str, default='Admin', help='Admin last name')
        parser.add_argument('--with-image', action='store_true', help='Attach default profile image')

    def create_default_profile_image(self):
        """
        Create a simple blue-colored default image using Pillow.
        """
        try:
            from PIL import Image
            img = Image.new('RGB', (200, 200), color='#2563eb')
            img_io = io.BytesIO()
            img.save(img_io, format='JPEG', quality=90)
            img_io.seek(0)
            return SimpleUploadedFile('admin_profile.jpg', img_io.getvalue(), content_type='image/jpeg')
        except ImportError:
            self.stdout.write(self.style.WARNING("⚠ Pillow (PIL) not installed. Skipping profile image."))
            return None

    def create_admin_role(self):
        """
        Create the Admin role and assign all available permissions.
        """
        admin_role, created = Role.objects.get_or_create(name='Admin')
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created 'Admin' role"))
        else:
            self.stdout.write(self.style.WARNING("⚠ 'Admin' role already exists"))

        all_permissions = Permission.objects.all()
        admin_role.permissions.set(all_permissions)
        admin_role.save()

        self.stdout.write(self.style.SUCCESS(f"✓ Assigned {all_permissions.count()} permissions to Admin role"))
        return admin_role

    def create_first_role(self):
        """
        Create the FirstRole role with limited permissions.
        """
        first_role, created = Role.objects.get_or_create(name='FirstRole')
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Created 'FirstRole' role"))
        else:
            self.stdout.write(self.style.WARNING("⚠ 'FirstRole' role already exists"))

        basic_permissions = Permission.objects.filter(codename__in=['view_user', 'change_user'])
        first_role.permissions.set(basic_permissions)
        first_role.save()

        self.stdout.write(self.style.SUCCESS(f"✓ Assigned {basic_permissions.count()} basic permissions to FirstRole"))

        if basic_permissions.exists():
            self.stdout.write("   FirstRole permissions:")
            for perm in basic_permissions:
                self.stdout.write(f"   - {perm.name}")

        return first_role

    def create_superuser(self, admin_role, options):
        """
        Create or update a superuser with the Admin role.
        """
        User = get_user_model()
        email = options['email']
        username = options['username']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        with_image = options['with_image']

        # Check if user already exists by email or username
        existing_user = User.objects.filter(email=email).first() or User.objects.filter(username=username).first()

        if existing_user:
            if existing_user.role != admin_role or not existing_user.is_superuser:
                existing_user.role = admin_role
                existing_user.is_superuser = True
                existing_user.is_staff = True
                existing_user.is_active = True
                existing_user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Updated existing user '{existing_user.username}' to Admin role"))
            else:
                self.stdout.write(self.style.WARNING(
                    f"⚠ Admin user with email '{email}' or username '{username}' already exists"))
            return existing_user

        # If not found, create a new superuser
        try:
            user_data = {
                'email': email,
                'username': username,
                'password': password,
                'first_name': first_name,
                'last_name': last_name,
                'role': admin_role
            }

            if with_image:
                profile_image = self.create_default_profile_image()
                if profile_image:
                    user_data['profile_image'] = profile_image

            user = User.objects.create_superuser(**user_data)

            self.stdout.write(self.style.SUCCESS("✓ Superuser created successfully!"))
            self.stdout.write(f"   Email: {email}")
            self.stdout.write(f"   Username: {username}")
            self.stdout.write(f"   Name: {first_name} {last_name}")
            self.stdout.write(f"   Role: {admin_role.name}")
            self.stdout.write(f"   Profile Image: {'Yes' if with_image and user.profile_image else 'No'}")

            return user

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error creating superuser: {str(e)}"))
            raise

    def display_summary(self):
        """
        Print a summary of roles and users.
        """
        User = get_user_model()
        self.stdout.write(self.style.HTTP_INFO("\n" + "="*60))
        self.stdout.write(self.style.HTTP_INFO("🎯 SEEDING SUMMARY"))
        self.stdout.write("="*60)

        roles = Role.objects.all().order_by('name')
        self.stdout.write(f"\n📋 ROLES ({roles.count()} total):")
        for role in roles:
            user_count = User.objects.filter(role=role).count()
            self.stdout.write(f"   • {role.name}: {role.permissions.count()} permissions, {user_count} users")

        total_users = User.objects.count()
        admin_users = User.objects.filter(is_superuser=True).count()
        active_users = User.objects.filter(is_active=True).count()

        self.stdout.write(f"\n👥 USERS ({total_users} total):")
        self.stdout.write(f"   • Total users: {total_users}")
        self.stdout.write(f"   • Admin users: {admin_users}")
        self.stdout.write(f"   • Active users: {active_users}")

        self.stdout.write(f"\n🔧 SYSTEM STATUS:")
        self.stdout.write(f"   • Admin role: {'✓ Ready' if Role.objects.filter(name='Admin').exists() else '✗ Missing'}")
        self.stdout.write(f"   • FirstRole: {'✓ Ready' if Role.objects.filter(name='FirstRole').exists() else '✗ Missing'}")
        self.stdout.write(f"   • Ready for user registration: ✓ Yes")

    def handle(self, *args, **options):
        """
        Main entry point for the command.
        """
        self.stdout.write(self.style.HTTP_INFO("🚀 Starting database seeding..."))
        self.stdout.write("="*60)

        try:
            # Step 1: Create Admin role
            self.stdout.write(self.style.HTTP_INFO("\n📝 Step 1: Creating Admin role"))
            admin_role = self.create_admin_role()

            # Step 2: Create FirstRole
            self.stdout.write(self.style.HTTP_INFO("\n📝 Step 2: Creating FirstRole"))
            self.create_first_role()

            # Step 3: Create superuser
            self.stdout.write(self.style.HTTP_INFO("\n📝 Step 3: Creating superuser"))
            self.create_superuser(admin_role, options)

            # Step 4: Display summary
            self.display_summary()

            self.stdout.write(self.style.SUCCESS("\n🎉 Database seeding completed successfully!"))
            self.stdout.write(self.style.HTTP_INFO("\n🔑 LOGIN CREDENTIALS:"))
            self.stdout.write(f"   URL: /admin/ or your login page")
            self.stdout.write(f"   Email: {options['email']}")
            self.stdout.write(f"   Password: {options['password']}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n💥 Seeding failed: {str(e)}"))
            raise

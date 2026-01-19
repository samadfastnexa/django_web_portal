"""
Django management command to set up default cart roles with permissions.

Run with:
    python manage.py setup_cart_roles
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role
from cart.models import Cart, Order


class Command(BaseCommand):
    help = 'Set up default roles with cart permissions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('🛒 Setting up Cart Roles and Permissions'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Get cart content types
        cart_ct = ContentType.objects.get_for_model(Cart)
        order_ct = ContentType.objects.get_for_model(Order)

        # Get all cart permissions
        cart_permissions = {
            'add_to_cart': Permission.objects.get(codename='add_to_cart', content_type=cart_ct),
            'manage_cart': Permission.objects.get(codename='manage_cart', content_type=cart_ct),
            'view_order_history': Permission.objects.get(codename='view_order_history', content_type=order_ct),
            'manage_orders': Permission.objects.get(codename='manage_orders', content_type=order_ct),
            'sync_orders_to_sap': Permission.objects.get(codename='sync_orders_to_sap', content_type=order_ct),
        }

        self.stdout.write('📋 Available cart permissions:')
        for name, perm in cart_permissions.items():
            self.stdout.write(f'  ✓ {name}: {perm}')

        # Create/Update Customer Role
        self.stdout.write('\n' + '-'*60)
        customer_role, created = Role.objects.get_or_create(name='Customer')
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Created "Customer" role'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  "Customer" role already exists (updating permissions)'))

        customer_perms = [
            cart_permissions['add_to_cart'],
            cart_permissions['manage_cart'],
            cart_permissions['view_order_history'],
        ]
        
        # Add permissions to role
        for perm in customer_perms:
            customer_role.permissions.add(perm)
        
        self.stdout.write(f'   Assigned {len(customer_perms)} permissions to Customer role:')
        for perm in customer_perms:
            self.stdout.write(f'     • {perm.codename}')

        # Create/Update Sales Agent Role
        self.stdout.write('\n' + '-'*60)
        sales_agent_role, created = Role.objects.get_or_create(name='Sales Agent')
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Created "Sales Agent" role'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  "Sales Agent" role already exists (updating permissions)'))

        sales_agent_perms = [
            cart_permissions['add_to_cart'],
            cart_permissions['manage_cart'],
            cart_permissions['view_order_history'],
            cart_permissions['manage_orders'],
        ]
        
        for perm in sales_agent_perms:
            sales_agent_role.permissions.add(perm)
        
        self.stdout.write(f'   Assigned {len(sales_agent_perms)} permissions to Sales Agent role:')
        for perm in sales_agent_perms:
            self.stdout.write(f'     • {perm.codename}')

        # Create/Update Order Manager Role
        self.stdout.write('\n' + '-'*60)
        manager_role, created = Role.objects.get_or_create(name='Order Manager')
        
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Created "Order Manager" role'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  "Order Manager" role already exists (updating permissions)'))

        manager_perms = [
            cart_permissions['view_order_history'],
            cart_permissions['manage_orders'],
            cart_permissions['sync_orders_to_sap'],
        ]
        
        for perm in manager_perms:
            manager_role.permissions.add(perm)
        
        self.stdout.write(f'   Assigned {len(manager_perms)} permissions to Order Manager role:')
        for perm in manager_perms:
            self.stdout.write(f'     • {perm.codename}')

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ Cart roles setup complete!'))
        self.stdout.write('='*60)
        
        self.stdout.write('\n📝 Summary:')
        self.stdout.write(f'  • Customer: {customer_role.permissions.filter(content_type__in=[cart_ct, order_ct]).count()} cart permissions')
        self.stdout.write(f'  • Sales Agent: {sales_agent_role.permissions.filter(content_type__in=[cart_ct, order_ct]).count()} cart permissions')
        self.stdout.write(f'  • Order Manager: {manager_role.permissions.filter(content_type__in=[cart_ct, order_ct]).count()} cart permissions')
        
        self.stdout.write('\n💡 Next steps:')
        self.stdout.write('  1. Assign roles to users in Django Admin')
        self.stdout.write('  2. Test API endpoints with assigned users')
        self.stdout.write('  3. View documentation in CART_PERMISSIONS_QUICK_SETUP.md')
        
        self.stdout.write('\n')

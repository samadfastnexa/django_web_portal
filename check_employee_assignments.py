#!/usr/bin/env python
"""
Check if all employees are assigned Company, Region, Zone, and Territory.
Usage: python manage.py shell < check_employee_assignments.py
Or: python check_employee_assignments.py
"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_portal'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from accounts.models import User, SalesStaffProfile
from FieldAdvisoryService.models import Territory

def check_employee_assignments():
    print("\n" + "="*80)
    print("EMPLOYEE ASSIGNMENT VERIFICATION")
    print("="*80)
    
    # Get all users
    all_users = User.objects.all()
    total_users = all_users.count()
    
    print(f"\n📊 Total Users: {total_users}")
    
    # Check who has sales profile
    users_with_profile = User.objects.filter(sales_profile__isnull=False).count()
    users_without_profile = total_users - users_with_profile
    
    print(f"✅ Users with SalesStaffProfile: {users_with_profile}")
    print(f"❌ Users without SalesStaffProfile: {users_without_profile}")
    
    if users_without_profile > 0:
        print("\n   Users without SalesStaffProfile:")
        without_profile = User.objects.filter(sales_profile__isnull=True)
        for user in without_profile[:10]:
            print(f"   - {user.id}: {user.username} ({user.email})")
    
    # Check assignments for users WITH SalesStaffProfile
    print("\n" + "-"*80)
    print("CHECKING ASSIGNMENTS FOR USERS WITH SALESSTAFFPROFILE")
    print("-"*80)
    
    users_with_profile_qs = User.objects.filter(sales_profile__isnull=False)
    
    # Company assignments (ManyToMany)
    users_with_company = 0
    users_without_company = 0
    for user in users_with_profile_qs:
        if user.sales_profile.companies.exists():
            users_with_company += 1
        else:
            users_without_company += 1
    
    print(f"\n📌 COMPANY Assignment:")
    print(f"   ✅ With Company: {users_with_company}")
    print(f"   ❌ Without Company: {users_without_company}")
    
    if users_without_company > 0:
        print("   \n   Users without Company:")
        count = 0
        for user in users_with_profile_qs:
            if not user.sales_profile.companies.exists():
                print(f"   - {user.id}: {user.username} ({user.email})")
                count += 1
                if count >= 10:
                    break
    
    # Region assignments (ManyToMany)
    users_with_region = 0
    users_without_region = 0
    for user in users_with_profile_qs:
        if user.sales_profile.regions.exists():
            users_with_region += 1
        else:
            users_without_region += 1
    
    print(f"\n📌 REGION Assignment:")
    print(f"   ✅ With Region: {users_with_region}")
    print(f"   ❌ Without Region: {users_without_region}")
    
    if users_without_region > 0:
        print("   \n   Users without Region:")
        count = 0
        for user in users_with_profile_qs:
            if not user.sales_profile.regions.exists():
                print(f"   - {user.id}: {user.username} ({user.email})")
                count += 1
                if count >= 10:
                    break
    
    # Zone assignments (ManyToMany)
    users_with_zone = 0
    users_without_zone = 0
    for user in users_with_profile_qs:
        if user.sales_profile.zones.exists():
            users_with_zone += 1
        else:
            users_without_zone += 1
    
    print(f"\n📌 ZONE Assignment:")
    print(f"   ✅ With Zone: {users_with_zone}")
    print(f"   ❌ Without Zone: {users_without_zone}")
    
    if users_without_zone > 0:
        print("   \n   Users without Zone:")
        count = 0
        for user in users_with_profile_qs:
            if not user.sales_profile.zones.exists():
                print(f"   - {user.id}: {user.username} ({user.email})")
                count += 1
                if count >= 10:
                    break
    
    # Territory assignments (ManyToMany)
    users_with_territory = 0
    users_without_territory = 0
    for user in users_with_profile_qs:
        if user.sales_profile.territories.exists():
            users_with_territory += 1
        else:
            users_without_territory += 1
    
    print(f"\n📌 TERRITORY Assignment:")
    print(f"   ✅ With at least 1 Territory: {users_with_territory}")
    print(f"   ❌ Without any Territory: {users_without_territory}")
    
    if users_without_territory > 0:
        print("   \n   Users without Territory:")
        count = 0
        for user in users_with_profile_qs:
            if not user.sales_profile.territories.exists():
                print(f"   - {user.id}: {user.username} ({user.email})")
                count += 1
                if count >= 10:
                    break
    
    # Summary - ALL assignments present
    print("\n" + "-"*80)
    print("SUMMARY - ALL REQUIRED ASSIGNMENTS")
    print("-"*80)
    
    fully_assigned = 0
    incomplete_list = []
    
    for user in users_with_profile_qs:
        profile = user.sales_profile
        has_company = profile.companies.exists()
        has_region = profile.regions.exists()
        has_zone = profile.zones.exists()
        has_territory = profile.territories.exists()
        
        if has_company and has_region and has_zone and has_territory:
            fully_assigned += 1
        else:
            incomplete_list.append((user, profile, has_company, has_region, has_zone, has_territory))
    
    incomplete = users_with_profile - fully_assigned
    
    print(f"\n🎯 Employees with ALL assignments (Company + Region + Zone + Territory): {fully_assigned}")
    print(f"⚠️  Employees with INCOMPLETE assignments: {incomplete}")
    
    if incomplete > 0:
        print(f"\n   Incomplete employee details (first 20):")
        for user, profile, has_company, has_region, has_zone, has_territory in incomplete_list[:20]:
            company = "✅" if has_company else "❌"
            region = "✅" if has_region else "❌"
            zone = "✅" if has_zone else "❌"
            territory = "✅" if has_territory else "❌"
            
            print(f"   - {user.id}: {user.username:20} | Company{company} Region{region} Zone{zone} Territory{territory}")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    check_employee_assignments()

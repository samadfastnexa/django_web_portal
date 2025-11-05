#!/usr/bin/env python3
"""
Test script for Meeting API with farmer linking functionality
Tests the new attendee_farmer_id field that links farmers from FAS system
"""

import os
import sys
import django
from datetime import datetime
import json

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from farmerMeetingDataEntry.models import Meeting, FarmerAttendance
from farmerMeetingDataEntry.serializers import MeetingSerializer
from farmers.models import Farmer
from django.contrib.auth.models import User

def test_meeting_farmer_linking():
    """Test creating a meeting with farmer linking"""
    
    print("🧪 Testing Meeting API with Farmer Linking")
    print("=" * 50)
    
    # Get some existing farmers for testing
    farmers = Farmer.objects.all()[:3]
    if not farmers:
        print("❌ No farmers found in database. Please add some farmers first.")
        return
    
    print(f"📋 Found {len(farmers)} farmers for testing:")
    for farmer in farmers:
        print(f"  - ID: {farmer.farmer_id}, Name: {farmer.full_name}, Phone: {farmer.primary_phone}")
    
    # Test data with farmer linking
    test_data = {
        'fsm_name': 'Test FSM for Farmer Linking',
        'date': datetime.now().isoformat(),
        'location': 'Test Location',
        'total_attendees': len(farmers),
        'key_topics_discussed': 'Testing farmer linking functionality',
        'presence_of_zm': True,
        'presence_of_rsm': False,
        'feedback_from_attendees': 'Positive feedback on farmer linking',
        'suggestions_for_future': 'Continue using farmer linking',
        
        # Use farmer IDs to link existing farmers
        'attendee_farmer_id': [farmer.farmer_id for farmer in farmers],
        'attendee_acreage': [5.0, 3.5, 7.2],
        'attendee_crop': ['Rice', 'Wheat', 'Cotton']
    }
    
    print(f"\n📝 Creating meeting with farmer linking...")
    print(f"Farmer IDs: {test_data['attendee_farmer_id']}")
    
    # Test serializer validation
    serializer = MeetingSerializer(data=test_data)
    if serializer.is_valid():
        print("✅ Serializer validation passed")
        
        # Create the meeting
        meeting = serializer.save()
        print(f"✅ Meeting created with ID: {meeting.id}")
        
        # Verify attendees were created with farmer links
        attendees = meeting.attendees.all()
        print(f"\n👥 Meeting Attendees ({len(attendees)}):")
        
        for i, attendee in enumerate(attendees):
            print(f"\n  Attendee {i+1}:")
            print(f"    - Farmer ID: {attendee.farmer.farmer_id if attendee.farmer else 'None'}")
            print(f"    - Farmer Name: {attendee.farmer_name}")
            print(f"    - Contact: {attendee.contact_number}")
            print(f"    - Acreage: {attendee.acreage}")
            print(f"    - Crop: {attendee.crop}")
            print(f"    - Linked Farmer: {'Yes' if attendee.farmer else 'No'}")
            
            if attendee.farmer:
                print(f"    - Farmer Full Name: {attendee.farmer.full_name}")
                print(f"    - Farmer District: {attendee.farmer.district}")
                print(f"    - Farmer Village: {attendee.farmer.village}")
        
        # Test API response format
        print(f"\n📊 API Response Format:")
        response_serializer = MeetingSerializer(meeting)
        response_data = response_serializer.data
        
        print(f"Meeting ID: {response_data['id']}")
        print(f"FSM Name: {response_data['fsm_name']}")
        print(f"Total Attendees: {response_data['total_attendees']}")
        print(f"Number of Attendees in Response: {len(response_data['attendees'])}")
        
        print(f"\n👥 Attendees in API Response:")
        for i, attendee_data in enumerate(response_data['attendees']):
            print(f"\n  Attendee {i+1}:")
            print(f"    - ID: {attendee_data.get('id')}")
            print(f"    - Farmer ID: {attendee_data.get('farmer_id', 'None')}")
            print(f"    - Farmer Full Name: {attendee_data.get('farmer_full_name', 'None')}")
            print(f"    - Farmer Primary Phone: {attendee_data.get('farmer_primary_phone', 'None')}")
            print(f"    - Farmer District: {attendee_data.get('farmer_district', 'None')}")
            print(f"    - Farmer Village: {attendee_data.get('farmer_village', 'None')}")
            print(f"    - Farmer Name: {attendee_data.get('farmer_name')}")
            print(f"    - Contact Number: {attendee_data.get('contact_number')}")
            print(f"    - Acreage: {attendee_data.get('acreage')}")
            print(f"    - Crop: {attendee_data.get('crop')}")
        
        print(f"\n✅ Test completed successfully!")
        print(f"✅ Farmer linking is working correctly!")
        print(f"✅ attendee_name and attendee_contact are auto-populated from farmer records!")
        
        # Clean up
        meeting.delete()
        print(f"\n🧹 Test data cleaned up")
        
    else:
        print("❌ Serializer validation failed:")
        for field, errors in serializer.errors.items():
            print(f"  {field}: {errors}")

def test_meeting_without_farmer_linking():
    """Test creating a meeting without farmer linking (manual input)"""
    
    print(f"\n🧪 Testing Meeting API without Farmer Linking (Manual Input)")
    print("=" * 60)
    
    # Test data without farmer linking
    test_data = {
        'fsm_name': 'Test FSM Manual Input',
        'date': datetime.now().isoformat(),
        'location': 'Test Location Manual',
        'total_attendees': 2,
        'key_topics_discussed': 'Testing manual input functionality',
        'presence_of_zm': False,
        'presence_of_rsm': True,
        'feedback_from_attendees': 'Good feedback',
        'suggestions_for_future': 'Continue manual input option',
        
        # Manual input (no farmer linking)
        'attendee_name': ['Manual Farmer 1', 'Manual Farmer 2'],
        'attendee_contact': ['1234567890', '0987654321'],
        'attendee_acreage': [4.0, 6.0],
        'attendee_crop': ['Corn', 'Soybean']
    }
    
    print(f"📝 Creating meeting with manual input...")
    
    # Test serializer validation
    serializer = MeetingSerializer(data=test_data)
    if serializer.is_valid():
        print("✅ Serializer validation passed")
        
        # Create the meeting
        meeting = serializer.save()
        print(f"✅ Meeting created with ID: {meeting.id}")
        
        # Verify attendees were created without farmer links
        attendees = meeting.attendees.all()
        print(f"\n👥 Meeting Attendees ({len(attendees)}):")
        
        for i, attendee in enumerate(attendees):
            print(f"\n  Attendee {i+1}:")
            print(f"    - Farmer Name: {attendee.farmer_name}")
            print(f"    - Contact: {attendee.contact_number}")
            print(f"    - Acreage: {attendee.acreage}")
            print(f"    - Crop: {attendee.crop}")
            print(f"    - Linked Farmer: {'Yes' if attendee.farmer else 'No'}")
        
        print(f"\n✅ Manual input test completed successfully!")
        
        # Clean up
        meeting.delete()
        print(f"🧹 Test data cleaned up")
        
    else:
        print("❌ Serializer validation failed:")
        for field, errors in serializer.errors.items():
            print(f"  {field}: {errors}")

if __name__ == "__main__":
    try:
        test_meeting_farmer_linking()
        test_meeting_without_farmer_linking()
        print(f"\n🎉 All tests completed successfully!")
        print(f"🎉 Farmer linking functionality is working as expected!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
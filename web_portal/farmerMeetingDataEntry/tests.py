from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from farmers.models import Farmer
from .models import FieldDay, FieldDayAttendance
from .serializers import FieldDaySerializer, FlexibleListField
from rest_framework import serializers


class FlexibleListFieldTest(TestCase):
    """Test the FlexibleListField custom field functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.field = FlexibleListField(child=serializers.CharField())
    
    def test_list_input(self):
        """Test that proper list input works correctly"""
        data = ['80', '84']
        result = self.field.to_internal_value(data)
        self.assertEqual(result, ['80', '84'])
    
    def test_integer_list_input(self):
        """Test that integer list input is converted to strings"""
        data = [80, 84]
        result = self.field.to_internal_value(data)
        self.assertEqual(result, ['80', '84'])
    
    def test_comma_separated_string_input(self):
        """Test that comma-separated string input is parsed correctly"""
        data = '80,84'
        result = self.field.to_internal_value(data)
        self.assertEqual(result, ['80', '84'])
    
    def test_comma_separated_string_with_spaces(self):
        """Test that comma-separated string with spaces is parsed correctly"""
        data = '80, 84, 90'
        result = self.field.to_internal_value(data)
        self.assertEqual(result, ['80', '84', '90'])
    
    def test_empty_string_input(self):
        """Test that empty string returns empty list"""
        data = ''
        result = self.field.to_internal_value(data)
        self.assertEqual(result, [])
    
    def test_whitespace_only_string(self):
        """Test that whitespace-only string returns empty list"""
        data = '   '
        result = self.field.to_internal_value(data)
        self.assertEqual(result, [])


class FieldDaySerializerTest(APITestCase):
    """Test the FieldDaySerializer with FlexibleListField"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test farmers
        self.farmer1 = Farmer.objects.create(
            farmer_id='FM01',
            full_name='Test Farmer 1',
            primary_phone='1234567890',
            district='Test District',
            village='Test Village'
        )
        
        self.farmer2 = Farmer.objects.create(
            farmer_id='FM02', 
            full_name='Test Farmer 2',
            primary_phone='0987654321',
            district='Test District 2',
            village='Test Village 2'
        )
        
        # Base field day data
        self.base_data = {
            'location': 'Test Location',
            'date': '2025-10-02T07:25:31.401000Z'
        }
    
    def test_attendee_farmer_id_as_list(self):
        """Test that attendee_farmer_id as list creates separate attendees"""
        data = {
            **self.base_data,
            'attendee_farmer_id': [str(self.farmer1.id), str(self.farmer2.id)]
        }
        
        serializer = FieldDaySerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        field_day = serializer.save(user=self.user)
        
        # Check that two separate attendees were created
        attendees = FieldDayAttendance.objects.filter(field_day=field_day)
        self.assertEqual(attendees.count(), 2)
        
        # Check that farmers are correctly linked
        farmer_ids = [attendee.farmer.id for attendee in attendees if attendee.farmer]
        self.assertIn(self.farmer1.id, farmer_ids)
        self.assertIn(self.farmer2.id, farmer_ids)
    
    def test_attendee_farmer_id_as_comma_separated_string(self):
        """Test that attendee_farmer_id as comma-separated string creates separate attendees"""
        data = {
            **self.base_data,
            'attendee_farmer_id': f'{self.farmer1.id},{self.farmer2.id}'
        }
        
        serializer = FieldDaySerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        field_day = serializer.save(user=self.user)
        
        # Check that two separate attendees were created
        attendees = FieldDayAttendance.objects.filter(field_day=field_day)
        self.assertEqual(attendees.count(), 2)
        
        # Check that farmers are correctly linked
        farmer_ids = [attendee.farmer.id for attendee in attendees if attendee.farmer]
        self.assertIn(self.farmer1.id, farmer_ids)
        self.assertIn(self.farmer2.id, farmer_ids)
    
    def test_attendee_farmer_id_with_spaces(self):
        """Test that comma-separated string with spaces works correctly"""
        data = {
            **self.base_data,
            'attendee_farmer_id': f'{self.farmer1.id}, {self.farmer2.id}'
        }
        
        serializer = FieldDaySerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        field_day = serializer.save(user=self.user)
        
        # Check that two separate attendees were created
        attendees = FieldDayAttendance.objects.filter(field_day=field_day)
        self.assertEqual(attendees.count(), 2)
    
    def test_single_farmer_id(self):
        """Test that single farmer ID works correctly"""
        data = {
            **self.base_data,
            'attendee_farmer_id': [str(self.farmer1.id)]
        }
        
        serializer = FieldDaySerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        field_day = serializer.save(user=self.user)
        
        # Check that one attendee was created
        attendees = FieldDayAttendance.objects.filter(field_day=field_day)
        self.assertEqual(attendees.count(), 1)
        
        # Check that farmer is correctly linked
        attendee = attendees.first()
        self.assertEqual(attendee.farmer.id, self.farmer1.id)
    
    def test_empty_attendee_farmer_id(self):
        """Test that empty attendee_farmer_id doesn't create attendees"""
        data = {
            **self.base_data,
            'attendee_farmer_id': []
        }
        
        serializer = FieldDaySerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        field_day = serializer.save(user=self.user)
        
        # Check that no attendees were created
        attendees = FieldDayAttendance.objects.filter(field_day=field_day)
        self.assertEqual(attendees.count(), 0)
    
    def test_nonexistent_farmer_id(self):
        """Test behavior with non-existent farmer ID"""
        data = {
            **self.base_data,
            'attendee_farmer_id': ['999999']  # Non-existent farmer ID
        }
        
        serializer = FieldDaySerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")
        
        field_day = serializer.save(user=self.user)
        
        # Check that an "Unknown Farmer" attendee was created
        attendees = FieldDayAttendance.objects.filter(field_day=field_day)
        self.assertEqual(attendees.count(), 1)
        
        attendee = attendees.first()
        self.assertIsNone(attendee.farmer)
        self.assertIn("Unknown Farmer", attendee.farmer_name)

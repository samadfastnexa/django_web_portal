from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Role
from .models import Farm

User = get_user_model()

class FarmModelTest(TestCase):
    def setUp(self):
        # Create a test role
        self.role = Role.objects.create(name='TestRole')
        
        # Create a simple test image
        test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b',
            content_type='image/jpeg'
        )
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=self.role,
            profile_image=test_image
        )
        self.farm = Farm.objects.create(
            name='Test Farm',
            owner=self.user,
            address='123 Test Street',
            geolocation='40.7128,-74.0060',  # NYC coordinates
            size=100.50,
            soil_type='loamy',
            ownership_details='Test ownership details'
        )

    def test_farm_creation_with_defaults(self):
        """Test that farm is created with correct default values"""
        self.assertTrue(self.farm.is_active)
        self.assertIsNone(self.farm.deleted_at)
        self.assertFalse(self.farm.is_deleted)
        self.assertIsNotNone(self.farm.created_at)
        self.assertIsNotNone(self.farm.updated_at)

    def test_soft_delete(self):
        """Test soft delete functionality"""
        self.assertFalse(self.farm.is_deleted)
        self.assertTrue(self.farm.is_active)
        
        # Perform soft delete
        self.farm.soft_delete()
        
        # Check that farm is soft deleted
        self.assertTrue(self.farm.is_deleted)
        self.assertFalse(self.farm.is_active)
        self.assertIsNotNone(self.farm.deleted_at)
        
        # Farm should still exist in database
        self.assertTrue(Farm.objects.filter(id=self.farm.id).exists())

    def test_restore_farm(self):
        """Test restore functionality"""
        # First soft delete the farm
        self.farm.soft_delete()
        self.assertTrue(self.farm.is_deleted)
        
        # Then restore it
        self.farm.restore()
        
        # Check that farm is restored
        self.assertFalse(self.farm.is_deleted)
        self.assertTrue(self.farm.is_active)
        self.assertIsNone(self.farm.deleted_at)

    def test_farm_str_representation(self):
        """Test string representation of farm"""
        expected = f"{self.farm.name} - {self.farm.owner}"
        self.assertEqual(str(self.farm), expected)

    def test_farm_ordering(self):
        """Test that farms are ordered by creation date (newest first)"""
        # Create another farm
        farm2 = Farm.objects.create(
            name='Test Farm 2',
            owner=self.user,
            address='456 Test Avenue',
            geolocation='40.7589,-73.9851',
            size=75.25,
            soil_type='sandy'
        )
        
        farms = Farm.objects.all()
        self.assertEqual(farms[0], farm2)  # Newest first
        self.assertEqual(farms[1], self.farm)

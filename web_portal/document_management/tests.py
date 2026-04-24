from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Attachment, AttachmentAssignment

User = get_user_model()


class AttachmentModelTest(TestCase):
    """Test cases for Attachment model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_attachment(self):
        """Test creating an attachment."""
        file_content = b"Test PDF content"
        file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")
        
        attachment = Attachment.objects.create(
            title="Test Attachment",
            description="Test Description",
            file=file,
            created_by=self.user
        )
        
        self.assertEqual(attachment.title, "Test Attachment")
        self.assertEqual(attachment.created_by, self.user)
        self.assertTrue(attachment.file)
    
    def test_attachment_expiry(self):
        """Test attachment expiry logic."""
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        
        # Create expired attachment
        past_date = timezone.now() - timedelta(days=1)
        attachment = Attachment.objects.create(
            title="Expired Attachment",
            file=file,
            created_by=self.user,
            expiry_date=past_date,
            status='active'
        )
        
        self.assertTrue(attachment.is_expired)
    
    def test_formatted_file_size(self):
        """Test file size formatting."""
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        
        attachment = Attachment.objects.create(
            title="Test",
            file=file,
            created_by=self.user
        )
        
        self.assertIn("B", attachment.formatted_file_size)


class AttachmentAssignmentTest(TestCase):
    """Test cases for AttachmentAssignment model."""
    
    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True
        )
        self.user = User.objects.create_user(
            username='employee',
            password='emp123'
        )
        
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        self.attachment = Attachment.objects.create(
            title="Test Attachment",
            file=file,
            created_by=self.admin
        )
    
    def test_create_assignment(self):
        """Test creating an assignment."""
        assignment = AttachmentAssignment.objects.create(
            attachment=self.attachment,
            user=self.user,
            assigned_by=self.admin
        )
        
        self.assertEqual(assignment.user, self.user)
        self.assertEqual(assignment.attachment, self.attachment)
        self.assertFalse(assignment.viewed)
        self.assertEqual(assignment.download_count, 0)
    
    def test_mark_as_viewed(self):
        """Test marking assignment as viewed."""
        assignment = AttachmentAssignment.objects.create(
            attachment=self.attachment,
            user=self.user,
            assigned_by=self.admin
        )
        
        assignment.mark_as_viewed()
        
        self.assertTrue(assignment.viewed)
        self.assertIsNotNone(assignment.viewed_at)
    
    def test_increment_download_count(self):
        """Test incrementing download counter."""
        assignment = AttachmentAssignment.objects.create(
            attachment=self.attachment,
            user=self.user,
            assigned_by=self.admin
        )
        
        assignment.increment_download_count()
        
        self.assertEqual(assignment.download_count, 1)
        self.assertIsNotNone(assignment.last_downloaded_at)


class AttachmentAPITest(APITestCase):
    """Test cases for Attachment API."""
    
    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        self.employee = User.objects.create_user(
            username='employee',
            password='emp123'
        )
        
        self.client = APIClient()
        
        # Create test attachment
        file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")
        self.attachment = Attachment.objects.create(
            title="Test Attachment",
            file=file,
            created_by=self.admin
        )
    
    def test_list_attachments_as_admin(self):
        """Test listing attachments as admin."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/documents/attachments/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_list_attachments_as_employee(self):
        """Test listing attachments as employee (should see only assigned)."""
        # Assign attachment to employee
        AttachmentAssignment.objects.create(
            attachment=self.attachment,
            user=self.employee,
            assigned_by=self.admin
        )
        
        self.client.force_authenticate(user=self.employee)
        response = self.client.get('/api/documents/attachments/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access."""
        response = self.client.get('/api/documents/attachments/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

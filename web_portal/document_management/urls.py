from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AttachmentViewSet, AttachmentAssignmentViewSet

app_name = 'document_management'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'attachments', AttachmentViewSet, basename='attachment')
router.register(r'assignments', AttachmentAssignmentViewSet, basename='assignment')

# Customize for Swagger documentation
# Add tags to endpoints
urlpatterns = [
    path('', include(router.urls)),
]

from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.shortcuts import redirect 

from django.conf import settings
from django.conf.urls.static import static
schema_view = get_schema_view(
   openapi.Info(
      title="web portal API",
      default_version='v1',
      description="web portal API for user management",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', lambda request: redirect('/admin/', permanent=False)), # Redirect root(http://127.0.0.1:8000) URL to admin
    path('admin/', admin.site.urls),
    
    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # App APIs
    path('api/', include('accounts.urls')),  # ✅ all accounts related routes
    path('api/complaints/',include('complaints.urls')),
    path('api/farmers/',include('farmers.urls')),
    path('api/',include('preferences.urls')),
    path('api/',include('attendance.urls')),
    path('api/',include('farmerMeetingDataEntry.urls')),
    path('api/field/',include('FieldAdvisoryService.urls')), 
    path('api/farm/',include('farm.urls')),
    path('api/sap/', include('sap_integration.urls')),
    path('api/crop-management/', include('crop_management.urls')),
     path('api/', include('crop_manage.urls')),  # <-- add this
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

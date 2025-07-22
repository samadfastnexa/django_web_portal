from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

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
    path('admin/', admin.site.urls),
    
    # Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # App APIs
    path('api/accounts/', include('accounts.urls')),  # ✅ all accounts related routes
    path('api/complaints/', include('complaints.urls')),
    path('api/farmers/', include('farmers.urls')),
    path('api/preferences/', include('preferences.urls')),
    path('FieldAdvisoryService/fas/', include('FieldAdvisoryService.urls')),
    path('api/', include('attendance.urls')),
    path('api/', include('farmerMeetingDataEntry.urls')),
]

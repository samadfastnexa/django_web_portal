"""
URL configuration for web_portal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls')) 
"""
from django.contrib import admin
from django.urls import path, include

from accounts.views import SignupView
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import SignupView, MyTokenObtainPairView
from django.urls import re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


from accounts.views import UserListAPIView
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
    path('signup/', SignupView.as_view(), name='signup'),
    #  path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # JWT login
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
  
    # Include all API routes from the accounts app
    path('api/complaints/', include('complaints.urls')),

     # Include all API routes from the farmers app
    path('api/farmers/', include('farmers.urls')),

# Include all API routes from the farmerMeetingDataEntry app
    path('api/', include('farmerMeetingDataEntry.urls')),
]

 
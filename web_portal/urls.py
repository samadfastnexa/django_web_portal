from django.urls import path, include
from django.contrib import admin
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
   openapi.Info(
      title="Your API",
      default_version='v1',
      # ...other info...
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # ...existing code...
    path('api/accounts/', include('accounts.urls')),  # Adjust path as needed
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # ...existing code...
    path('admin/', admin.site.urls),
]

# Ensure admin dashboard subheading uses custom text instead of default "Site administration"
admin.site.index_title = "Tarzan Administration"
admin.site.site_header = "Tarzan Admin Panel by Fastnexa"
admin.site.site_title = "Tarzan Management Admin"
from django.urls import path
from .views import get_business_partner_data

urlpatterns = [
    # Unified API for Frontend
    path('business-partner/<str:card_code>/', get_business_partner_data, name='unified_bp_api'),
]
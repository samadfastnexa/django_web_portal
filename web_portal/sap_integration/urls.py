from django.urls import path
from .views import SAPBusinessPartnerView

urlpatterns = [
    path('bp/<str:card_code>/', SAPBusinessPartnerView.as_view(), name='sap_bp'),
]
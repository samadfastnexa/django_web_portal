from django.urls import path
from .views import (
    get_business_partner_data,
    list_policies,
    list_db_policies,
    sync_policies,
    policy_list_page,
)

urlpatterns = [
    # Unified API for Frontend
    path('business-partner/<str:card_code>/', get_business_partner_data, name='unified_bp_api'),
    path('policies/', list_policies, name='sap_policies'),
    # DB-backed policies APIs and page
    path('policy-records/', list_db_policies, name='policy_records'),
    path('policies/sync/', sync_policies, name='policies_sync'),
    path('policies/view/', policy_list_page, name='policies_page'),
]
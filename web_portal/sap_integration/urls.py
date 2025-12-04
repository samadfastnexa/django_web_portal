from django.urls import path
from .views import (
    get_business_partners_list,
    get_business_partner_detail,
    policy_customer_balance_list,
    policy_customer_balance_detail,
    list_policies,
    list_db_policies,
    sync_policies,
    policy_list_page,
)

urlpatterns = [
    # Unified API for Frontend - card_code is optional via two endpoints
    path('business-partner/', get_business_partners_list, name='unified_bp_api_list'),
    path('business-partner/<str:card_code>/', get_business_partner_detail, name='unified_bp_api'),
    # Policy Customer Balance - card_code is optional via two endpoints
    path('policy-customer-balance/', policy_customer_balance_list, name='policy_customer_balance_list'),
    path('policy-customer-balance/<str:card_code>/', policy_customer_balance_detail, name='policy_customer_balance_detail'),
    path('policies/', list_policies, name='sap_policies'),
    # DB-backed policies APIs and page
    path('policy-records/', list_db_policies, name='policy_records'),
    path('policies/sync/', sync_policies, name='policies_sync'),
    path('policies/view/', policy_list_page, name='policies_page'),
]

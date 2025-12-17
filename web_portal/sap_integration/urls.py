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
    warehouse_for_item_api,
    contact_persons_api,
    project_balance_api,
    customer_addresses_api,
    territories_full_api,
    cwl_full_api,
    customer_lov_api,
    item_lov_api,
    projects_lov_api,
    crop_lov_api,
    sales_orders_api,
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
    path('warehouse-for-item/', warehouse_for_item_api, name='warehouse_for_item_api'),
    path('contact-persons/', contact_persons_api, name='contact_persons_api'),
    path('project-balance/', project_balance_api, name='project_balance_api'),
    path('customer-addresses/', customer_addresses_api, name='customer_addresses_api'),
    path('territories-full/', territories_full_api, name='territories_full_api'),
    path('cwl-full/', cwl_full_api, name='cwl_full_api'),
    path('customer-lov/', customer_lov_api, name='customer_lov_api'),
    path('item-lov/', item_lov_api, name='item_lov_api'),
    path('projects-lov/', projects_lov_api, name='projects_lov_api'),
    path('crop-lov/', crop_lov_api, name='crop_lov_api'),
    path('sales-orders/', sales_orders_api, name='sales_orders_api'),
]

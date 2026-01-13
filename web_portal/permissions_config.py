# All Custom Permissions for AgriGenie System
# This file is used by the migration to create permissions

CUSTOM_PERMISSIONS = {
    # SAP Integration / HANA Connect
    'sap_integration': {
        'HanaConnect': [
            ('access_hana_connect', 'Can access HANA Connect dashboard'),
            ('view_policy_balance', 'Can view policy balance reports'),
            ('view_customer_data', 'Can view customer data'),
            ('view_item_master', 'Can view item master list'),
            ('view_sales_reports', 'Can view sales vs achievement reports'),
            ('sync_policies', 'Can sync policies from SAP'),
            ('post_to_sap', 'Can post data to SAP'),
        ],
        'Policy': [
            ('manage_policies', 'Can manage policy records'),
        ]
    },
    
    # Field Advisory Service
    'FieldAdvisoryService': {
        'Dealer': [
            ('manage_dealers', 'Can add/edit/delete dealers'),
            ('view_dealer_reports', 'Can view dealer reports'),
            ('approve_dealer_requests', 'Can approve dealer requests'),
        ],
        'Company': [
            ('manage_companies', 'Can manage companies'),
        ],
        'Region': [
            ('manage_regions', 'Can manage regions'),
        ],
        'Zone': [
            ('manage_zones', 'Can manage zones'),
        ],
        'Territory': [
            ('manage_territories', 'Can manage territories'),
        ],
    },
    
    # Crop Management
    'crop_management': {
        'Crop': [
            ('manage_crops', 'Can add/edit/delete crops'),
            ('view_crop_analytics', 'Can view crop analytics'),
        ],
        'CropVariety': [
            ('manage_varieties', 'Can manage crop varieties'),
        ],
        'YieldData': [
            ('manage_yield_data', 'Can manage yield data'),
            ('view_yield_analytics', 'Can view yield analytics'),
        ],
        'FarmingPractice': [
            ('manage_farming_practices', 'Can manage farming practices'),
        ],
        'CropResearch': [
            ('manage_research', 'Can manage crop research data'),
        ],
    },
    
    # Crop Manage (Trials)
    'crop_manage': {
        'Trial': [
            ('manage_trials', 'Can add/edit/delete field trials'),
            ('view_trial_results', 'Can view trial results'),
        ],
        'TrialTreatment': [
            ('manage_treatments', 'Can manage trial treatments'),
        ],
        'Product': [
            ('manage_products', 'Can manage trial products'),
        ],
    },
    
    # Farmers
    'farmers': {
        'Farmer': [
            ('manage_farmers', 'Can add/edit/delete farmer records'),
            ('view_farmer_reports', 'Can view farmer statistics'),
            ('export_farmer_data', 'Can export farmer data'),
        ],
    },
    
    # Farm Management
    'farm': {
        'Farm': [
            ('manage_farms', 'Can add/edit/delete farms'),
            ('view_farm_analytics', 'Can view farm analytics'),
        ],
    },
    
    # Attendance
    'attendance': {
        'Attendance': [
            ('manage_attendance', 'Can mark/edit attendance'),
            ('view_attendance_reports', 'Can view attendance reports'),
        ],
        'AttendanceRequest': [
            ('manage_attendance_requests', 'Can manage attendance requests'),
            ('approve_leave_requests', 'Can approve leave requests'),
        ],
    },
    
    # Complaints
    'complaints': {
        'Complaint': [
            ('manage_complaints', 'Can add/edit/resolve complaints'),
            ('view_complaint_reports', 'Can view complaint reports'),
            ('assign_complaints', 'Can assign complaints to staff'),
        ],
    },
    
    # Meetings
    'farmerMeetingDataEntry': {
        'Meeting': [
            ('manage_meetings', 'Can add/edit meetings'),
            ('view_meeting_reports', 'Can view meeting reports'),
        ],
        'FieldDay': [
            ('manage_field_days', 'Can manage field days'),
        ],
    },
    
    # KindWise
    'kindwise': {
        'KindwiseIdentification': [
            ('use_plant_identification', 'Can use plant identification API'),
            ('view_identification_history', 'Can view identification history'),
        ],
    },
    
    # Accounts / User Management
    'accounts': {
        'User': [
            ('manage_users', 'Can add/edit users'),
            ('view_user_reports', 'Can view user reports'),
        ],
        'Role': [
            ('manage_roles', 'Can manage roles and permissions'),
        ],
        'SalesStaffProfile': [
            ('manage_sales_staff', 'Can manage sales staff profiles'),
        ],
    },
    
    # General Ledger
    'general_ledger': {
        'GeneralLedger': [
            ('view_ledger', 'Can view general ledger entries'),
            ('export_ledger', 'Can export ledger data'),
        ],
    },
    
    # Analytics
    'analytics': {
        'DashboardAnalytics': [
            ('view_dashboard', 'Can access analytics dashboard'),
            ('view_sales_analytics', 'Can view sales analytics'),
            ('view_farmer_analytics', 'Can view farmer analytics'),
            ('export_analytics', 'Can export analytics reports'),
        ],
    },
    
    # Settings
    'preferences': {
        'Setting': [
            ('manage_settings', 'Can manage system settings'),
            ('view_settings', 'Can view system settings'),
        ],
    },
}

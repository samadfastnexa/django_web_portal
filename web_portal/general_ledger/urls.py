"""
URL Configuration for General Ledger App
"""
from django.urls import path
from . import views
from .sap_journal_entry_api import (
    export_journal_entry_ledger_sap_pdf_api,
    sap_journal_entry_health_api,
)

app_name = 'general_ledger'

urlpatterns = [
    # API Endpoints for Mobile/React App
    path('api/general-ledger/', views.general_ledger_api, name='general_ledger_api'),
    path('api/general-ledger/export-excel/', views.export_ledger_excel_api, name='export_ledger_excel_api'),
    path('api/general-ledger/export-pdf/', views.export_ledger_pdf_api, name='export_ledger_pdf_api'),
    path('api/general-ledger/sap-journal-entry/export-pdf/', export_journal_entry_ledger_sap_pdf_api, name='export_journal_entry_ledger_sap_pdf_api'),
    path('api/general-ledger/sap-journal-entry/health/', sap_journal_entry_health_api, name='sap_journal_entry_health_api'),
    path('api/chart-of-accounts/', views.chart_of_accounts_api, name='chart_of_accounts_api'),
    path('api/transaction-types/', views.transaction_types_api, name='transaction_types_api'),
    path('api/business-partners/', views.business_partners_api, name='business_partners_api'),
    path('api/projects/', views.projects_api, name='projects_api'),
    
    # Note: Admin routes are registered in main urls.py with admin_site.admin_view() wrapper
]

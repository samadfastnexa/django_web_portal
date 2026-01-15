#!/usr/bin/env python
"""
Test script to verify the business partner endpoint with database parameter.
This tests both 4B-BIO and 4B-ORANG databases.
"""

import os
import sys
import django
from pathlib import Path

# Add the web_portal directory to the path
web_portal_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(web_portal_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from sap_integration.views import get_business_partner_data

def add_session_to_request(request):
    """Add session to the request"""
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request

def test_business_partner_with_database():
    """Test the business partner endpoint with database parameter"""
    factory = RequestFactory()
    
    # Test 1: Orange database with OCR00001
    print("\n" + "="*60)
    print("Test 1: Business Partner with Orange Database")
    print("="*60)
    print("Request: GET /api/sap/business-partner/OCR00001/?database=4B-ORANG")
    
    request = factory.get('/api/sap/business-partner/OCR00001/?database=4B-ORANG')
    request = add_session_to_request(request)
    
    try:
        response = get_business_partner_data(request, card_code='OCR00001')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.data}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Business partner retrieved from Orange database")
        else:
            print("❌ FAILED: Unexpected status code")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    # Test 2: BIO database (default)
    print("\n" + "="*60)
    print("Test 2: Business Partner with BIO Database (Default)")
    print("="*60)
    print("Request: GET /api/sap/business-partner/?database=4B-BIO")
    
    request = factory.get('/api/sap/business-partner/?database=4B-BIO')
    request = add_session_to_request(request)
    
    try:
        response = get_business_partner_data(request, card_code=None)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print(f"Total Partners: {data.get('count', 0)}")
            if data.get('data'):
                print(f"First Partner: {data['data'][0]}")
            print("✅ SUCCESS: Business partners listed from BIO database")
        else:
            print("❌ FAILED: Unexpected status code")
            print(f"Response: {response.data}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == '__main__':
    test_business_partner_with_database()

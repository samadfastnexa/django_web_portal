"""
Test script for Policy Project Link API endpoint
Demonstrates how to fetch policy-project relationships for a customer
"""

import requests
import json

# Base URL (adjust to your server)
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/sap/policy-project-link/"

def test_policy_project_link():
    """Test fetching policy-project links for a customer"""
    
    print("=" * 80)
    print("Testing Policy Project Link API")
    print("=" * 80)
    
    # Test 1: Get policy-project links for a customer (BIO database)
    print("\n1. Getting policy-project links for customer BIC00611 (4B-BIO-app)")
    print("-" * 80)
    
    params = {
        'database': '4B-BIO-app',
        'card_code': 'BIC00611',
        'page_size': 10
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success'):
            print(f"✓ Success! Found {data['count']} policy-project links")
            print(f"  Page {data['page']} of {data['num_pages']}")
            print(f"\n  Sample results:")
            for idx, link in enumerate(data['data'][:3], 1):
                print(f"\n    {idx}. Policy DocEntry: {link.get('policy_doc_entry')}")
                print(f"       Policy Name: {link.get('policy_name')}")
                print(f"       Project Code: {link.get('project_code')}")
                print(f"       Project Name: {link.get('project_name')}")
                print(f"       Active: {link.get('project_active')}")
                print(f"       Valid Until: {link.get('project_valid_to')}")
                print(f"       Customer: {link.get('bp_code')}")
        else:
            print(f"✗ Error: {data.get('error')}")
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
    
    # Test 2: Query ORANG database
    print("\n2. Getting policy-project links from ORANG database")
    print("-" * 80)
    
    params = {
        'database': '4B-ORANG-app',
        'card_code': 'C-00001',
        'page_size': 5
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success'):
            print(f"✓ Success! Found {data['count']} links")
            print(f"\n  Results:")
            for idx, link in enumerate(data['data'], 1):
                print(f"    {idx}. Policy {link.get('policy_doc_entry')}: {link.get('project_name')}")
        else:
            print(f"✗ Error: {data.get('error')}")
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
    
    # Test 3: Validation - request without card_code
    print("\n3. Testing validation - request without card_code")
    print("-" * 80)
    
    params = {
        'database': '4B-BIO-app',
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params)
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✓ Validation working! Error: {data.get('error')}")
        else:
            print(f"✗ Unexpected: Request should have failed")
    
    except requests.exceptions.RequestException as e:
        print(f"Request result: {str(e)}")
    
    # Test 4: Pagination
    print("\n4. Testing pagination")
    print("-" * 80)
    
    params = {
        'database': '4B-BIO-app',
        'card_code': 'BIC00611',
        'page': 1,
        'page_size': 3
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success'):
            print(f"✓ Page {data['page']} of {data['num_pages']} (Total: {data['count']} items)")
            print(f"  Page size: {data['page_size']}")
            
            if data.get('num_pages', 0) > 1:
                # Try fetching page 2
                params['page'] = 2
                response = requests.get(API_ENDPOINT, params=params)
                data2 = response.json()
                print(f"✓ Page 2: Found {len(data2['data'])} items")
        else:
            print(f"✗ Error: {data.get('error')}")
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
    
    print("\n" + "=" * 80)
    print("API Endpoint Documentation:")
    print("=" * 80)
    print(f"URL: {API_ENDPOINT}")
    print("\nRequired Parameters:")
    print("  - card_code: Business Partner CardCode (e.g., 'BIC00611')")
    print("\nOptional Parameters:")
    print("  - database: '4B-BIO-app' or '4B-ORANG-app' (defaults to BIO)")
    print("  - page: Page number (default: 1)")
    print("  - page_size: Items per page (default: 50)")
    print("\nExample URLs:")
    print(f"  1. Basic: {API_ENDPOINT}?card_code=BIC00611")
    print(f"  2. ORANG DB: {API_ENDPOINT}?card_code=C-00001&database=4B-ORANG-app")
    print(f"  3. Paginated: {API_ENDPOINT}?card_code=BIC00611&page=2&page_size=20")
    print("=" * 80)

if __name__ == '__main__':
    test_policy_project_link()

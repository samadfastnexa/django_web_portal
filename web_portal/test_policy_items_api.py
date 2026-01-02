"""
Test script for Policy Items for Customer API endpoint
Demonstrates how to fetch all items in a specific policy for a specific customer
"""

import requests
import json

# Base URL (adjust to your server)
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/sap/policy-items/"

def test_policy_items():
    """Test fetching items in a policy"""
    
    print("=" * 80)
    print("Testing Policy Items for Customer API")
    print("=" * 80)
    
    # Test 1: Get all items in policy 18 (BIO database)
    print("\n1. Getting all items in policy DocEntry=18 (4B-BIO-app)")
    print("-" * 80)
    
    params = {
        'database': '4B-BIO-app',
        'doc_entry': '18',
        'page_size': 10
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success'):
            print(f"✓ Success! Found {data['count']} items")
            print(f"  Page {data['page']} of {data['num_pages']}")
            print(f"\n  Sample items:")
            for idx, item in enumerate(data['data'][:3], 1):
                print(f"    {idx}. ItemCode: {item.get('ItemCode')}")
                print(f"       ItemName: {item.get('ItemName')}")
                print(f"       Unit Price: {item.get('unit_price')} {item.get('Currency', '')}")
                print(f"       Policy: {item.get('policy_name')} (DocEntry: {item.get('policy_doc_entry')})")
                print(f"       Valid: {item.get('valid_from')} to {item.get('valid_to')}")
                print()
        else:
            print(f"✗ Error: {data.get('error')}")
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
    
    # Test 2: Get items in policy filtered by specific customer
    print("\n2. Getting items in policy DocEntry=18 for specific customer (ORANG database)")
    print("-" * 80)
    
    params = {
        'database': '4B-ORANG-app',
        'doc_entry': '18',
        'card_code': 'C-00001',  # Replace with actual CardCode
        'page_size': 5
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('success'):
            print(f"✓ Success! Found {data['count']} items for customer {params['card_code']}")
            print(f"  Page {data['page']} of {data['num_pages']}")
            print(f"\n  Items:")
            for idx, item in enumerate(data['data'], 1):
                print(f"    {idx}. {item.get('ItemCode')} - {item.get('ItemName')}")
                print(f"       Price: {item.get('unit_price')} {item.get('Currency', '')}")
                print(f"       BP Code: {item.get('bp_code')}")
                print()
        else:
            print(f"✗ Error: {data.get('error')}")
    
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
    
    # Test 3: Test without doc_entry (should fail)
    print("\n3. Testing validation - request without doc_entry")
    print("-" * 80)
    
    params = {
        'database': '4B-BIO-app',
    }
    
    try:
        response = requests.get(API_ENDPOINT, params=params)
        
        data = response.json()
        
        if not data.get('success'):
            print(f"✓ Validation working! Error message: {data.get('error')}")
        else:
            print(f"✗ Unexpected: Request should have failed")
    
    except requests.exceptions.RequestException as e:
        print(f"✓ Request properly rejected: {str(e)}")
    
    print("\n" + "=" * 80)
    print("API Endpoint Documentation:")
    print("=" * 80)
    print(f"URL: {API_ENDPOINT}")
    print("\nRequired Parameters:")
    print("  - doc_entry: Policy DocEntry (e.g., '18')")
    print("\nOptional Parameters:")
    print("  - database: '4B-BIO-app' or '4B-ORANG-app' (defaults to BIO)")
    print("  - card_code: Business Partner CardCode to filter by specific customer")
    print("  - page: Page number (default: 1)")
    print("  - page_size: Items per page (default: 50)")
    print("\nExample URLs:")
    print(f"  1. All items in policy: {API_ENDPOINT}?doc_entry=18")
    print(f"  2. Items for customer: {API_ENDPOINT}?doc_entry=18&card_code=C-00001")
    print(f"  3. ORANG database: {API_ENDPOINT}?doc_entry=18&database=4B-ORANG-app")
    print("=" * 80)

if __name__ == '__main__':
    test_policy_items()

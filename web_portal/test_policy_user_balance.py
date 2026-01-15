#!/usr/bin/env python
"""
Test script to demonstrate the user parameter in policy-customer-balance endpoint
"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test 1: Get all policy customer balances
print("=" * 80)
print("TEST 1: Get all policy customer balances (no filters)")
print("=" * 80)
url = f"{BASE_URL}/api/sap/policy-customer-balance/?database=4B-BIO&limit=5"
response = requests.get(url)
print(f"URL: {url}")
print(f"Status Code: {response.status_code}")
print(f"Response Count: {response.json().get('count', 0)}")
print()

# Test 2: Get policy balances for a specific user by ID
print("=" * 80)
print("TEST 2: Get policy balances for user by ID (e.g., user=1)")
print("=" * 80)
url = f"{BASE_URL}/api/sap/policy-customer-balance/?database=4B-BIO&user=1"
response = requests.get(url)
print(f"URL: {url}")
print(f"Status Code: {response.status_code}")
data = response.json()
print(f"Response Count: {data.get('count', 0)}")
if data.get('success'):
    print("Sample data:")
    if data.get('data'):
        print(json.dumps(data['data'][0], indent=2, default=str))
else:
    print(f"Error: {data.get('error')}")
print()

# Test 3: Get policy balances for a specific user by username
print("=" * 80)
print("TEST 3: Get policy balances for user by username (e.g., user=john_dealer)")
print("=" * 80)
url = f"{BASE_URL}/api/sap/policy-customer-balance/?database=4B-BIO&user=john_dealer"
response = requests.get(url)
print(f"URL: {url}")
print(f"Status Code: {response.status_code}")
data = response.json()
print(f"Response Count: {data.get('count', 0)}")
if data.get('success'):
    print("Sample data:")
    if data.get('data'):
        print(json.dumps(data['data'][0], indent=2, default=str))
else:
    print(f"Error: {data.get('error')}")
print()

# Test 4: Get specific customer balance by card code
print("=" * 80)
print("TEST 4: Get specific customer balance by card code")
print("=" * 80)
url = f"{BASE_URL}/api/sap/policy-customer-balance/ORC00002/?database=4B-ORANG"
response = requests.get(url)
print(f"URL: {url}")
print(f"Status Code: {response.status_code}")
data = response.json()
print(f"Response Count: {data.get('count', 0)}")
if data.get('success'):
    print("Sample data:")
    if data.get('data'):
        print(json.dumps(data['data'][0], indent=2, default=str))
print()

# Test 5: Invalid user
print("=" * 80)
print("TEST 5: Invalid user (should return 404)")
print("=" * 80)
url = f"{BASE_URL}/api/sap/policy-customer-balance/?database=4B-BIO&user=nonexistent_user"
response = requests.get(url)
print(f"URL: {url}")
print(f"Status Code: {response.status_code}")
data = response.json()
print(f"Error: {data.get('error')}")

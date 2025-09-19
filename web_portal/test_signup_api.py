import requests
import json

# Test data for signup API
import time
unique_id = str(int(time.time()))
test_data = {
    "username": f"testsales{unique_id}",
    "email": f"testsales{unique_id}@example.com",
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "Sales",
    "is_sales_staff": True,
    "employee_code": "EMP001",
    "phone_number": "+1234567890",
    "address": "123 Test Street",
    "designation": "MTO",
    "company": 1,  # Assuming company ID 1 exists
    "region": 1,   # Assuming region ID 1 exists
    "zone": 1,     # Assuming zone ID 1 exists
    "territory": 1, # Assuming territory ID 1 exists
    "sick_leave_quota": 10,
    "casual_leave_quota": 15,
    "others_leave_quota": 5
}

url = "http://localhost:8000/api/signup/"

print("Testing signup API...")
print(f"URL: {url}")
print(f"Data: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(url, data=test_data)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 201:
        print("✅ Signup successful!")
        print(f"Response Data: {response.json()}")
    else:
        print("❌ Signup failed!")
        print(f"Response Text: {response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")
except json.JSONDecodeError as e:
    print(f"❌ JSON decode error: {e}")
    print(f"Response text: {response.text}")
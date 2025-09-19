import requests
import json

# Test data for creating a farmer
test_data = {
    "first_name": "Test",
    "last_name": "User",
    "primary_phone": "03001234567",
    "village": "TestVillage",
    "district": "TestDistrict",
    "address": "Test Address",
    "tehsil": "TestTehsil",
    "province": "TestProvince",
    "gender": "male",
    "farm_ownership_type": "owned",
    "farming_experience": "beginner",
    "main_crops_grown": "wheat"
}

# Test farmer creation without farmer_id (should auto-generate)
print("Testing farmer creation without farmer_id...")
response = requests.post(
    "http://localhost:8000/api/farmers/",
    json=test_data,
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 201:
    farmer_data = response.json()
    print(f"\nFarmer created successfully!")
    print(f"Generated farmer_id: {farmer_data.get('farmer_id')}")
    print(f"Full name: {farmer_data.get('full_name')}")
else:
    print(f"\nError creating farmer: {response.text}")

# Test farmer creation with custom farmer_id
print("\n" + "="*50)
print("Testing farmer creation with custom farmer_id...")
test_data_with_id = test_data.copy()
test_data_with_id["farmer_id"] = "CUSTOM2025001"
test_data_with_id["first_name"] = "Custom"
test_data_with_id["last_name"] = "ID"
test_data_with_id["primary_phone"] = "03009876543"

response2 = requests.post(
    "http://localhost:8000/api/farmers/",
    json=test_data_with_id,
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response2.status_code}")
print(f"Response: {response2.text}")

if response2.status_code == 201:
    farmer_data2 = response2.json()
    print(f"\nFarmer created successfully!")
    print(f"Custom farmer_id: {farmer_data2.get('farmer_id')}")
    print(f"Full name: {farmer_data2.get('full_name')}")
else:
    print(f"\nError creating farmer: {response2.text}")
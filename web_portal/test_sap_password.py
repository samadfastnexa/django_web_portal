#!/usr/bin/env python
"""
SAP Password Test - Try different password variations
"""
import http.client
import ssl
import json
import os
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

print("=" * 80)
print("SAP PASSWORD TEST")
print("=" * 80)

# Test different password variations
passwords_to_test = [
    ('From .env SAP_PASSWORD', os.environ.get('SAP_PASSWORD', '')),
    ('Prompt - Enter the actual password', None),  # Will prompt
]

config = {
    'host': os.environ.get('SAP_B1S_HOST', 'fourbtest.vdc.services'),
    'port': int(os.environ.get('SAP_B1S_PORT', 50000)),
    'base_path': os.environ.get('SAP_B1S_BASE_PATH', '/b1s/v2'),
    'username': os.environ.get('SAP_USERNAME', 'Fast01'),
    'company_db': os.environ.get('SAP_COMPANY_DB', '4B-BIO_APP'),
}

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def test_login(username, password, company_db):
    """Test SAP login with given credentials"""
    login_data = {
        'UserName': username,
        'Password': password,
        'CompanyDB': company_db
    }
    
    try:
        conn = http.client.HTTPSConnection(
            config['host'], 
            config['port'], 
            context=ssl_context,
            timeout=30
        )
        
        headers = {'Content-Type': 'application/json'}
        login_path = f"{config['base_path']}/Login"
        
        conn.request("POST", login_path, json.dumps(login_data), headers)
        response = conn.getresponse()
        response_data = response.read()
        
        conn.close()
        
        if response.status == 200:
            login_response = json.loads(response_data.decode('utf-8'))
            session_id = login_response.get('SessionId')
            return True, session_id
        else:
            error_data = json.loads(response_data.decode('utf-8'))
            return False, error_data.get('error', {}).get('message', 'Unknown error')
    except Exception as e:
        return False, str(e)

print(f"\nConfiguration:")
print(f"  Host: {config['host']}:{config['port']}")
print(f"  Company DB: {config['company_db']}")
print(f"  Username: {config['username']}")
print("\n" + "-" * 80)

# Test password from .env
env_password = os.environ.get('SAP_PASSWORD', '')
if env_password:
    print(f"\n1. Testing password from .env: {env_password[:3]}{'*' * (len(env_password) - 3)}")
    success, result = test_login(config['username'], env_password, config['company_db'])
    if success:
        print(f"   ✓ SUCCESS! Session ID: {result}")
        print("\n   The .env password is CORRECT!")
    else:
        print(f"   ✗ FAILED: {result}")
        print("\n   The .env password is INCORRECT!")

# Prompt for correct password
print("\n2. Please enter the CORRECT password that works in Postman:")
print("   (The one you use in Postman for user 'Fast01')")
try:
    correct_password = input("   Password: ").strip()
    if correct_password:
        print(f"\n   Testing password: {correct_password[:3]}{'*' * max(0, len(correct_password) - 3)}")
        success, result = test_login(config['username'], correct_password, config['company_db'])
        if success:
            print(f"   ✓ SUCCESS! Session ID: {result}")
            print(f"\n   ✅ SOLUTION FOUND!")
            print(f"   Update your .env file with:")
            print(f"   SAP_PASSWORD={correct_password}")
        else:
            print(f"   ✗ FAILED: {result}")
    else:
        print("   No password entered, skipping test")
except KeyboardInterrupt:
    print("\n   Test cancelled")
except EOFError:
    print("\n   (Running in non-interactive mode)")

print("\n" + "=" * 80)
print("IMPORTANT:")
print("=" * 80)
print("The password in your .env might be wrong. Common issues:")
print("  1. Password has special characters that need escaping")
print("  2. Copy-paste error from Postman")
print("  3. Different password for Service Layer vs HANA")
print("\nYour Postman shows it works with user 'Fast01', so the password")
print("you use in Postman is the correct one. Copy it EXACTLY to .env")
print("=" * 80)

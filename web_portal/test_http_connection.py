import http.client
import json
import os
from dotenv import load_dotenv

load_dotenv()

host = os.environ.get('SAP_B1S_HOST', 'fourb.vdc.services')
port = int(os.environ.get('SAP_B1S_PORT', 5588))
username = os.environ.get('SAP_USERNAME')
password = os.environ.get('SAP_PASSWORD')

print(f"Testing HTTP connection to {host}:{port}")
print(f"Username: {username}")

# Test with plain HTTP
try:
    conn = http.client.HTTPConnection(host, port, timeout=10)
    
    # Try login
    login_data = {
        "CompanyDB": "4B-BIO_APP",
        "UserName": username,
        "Password": password
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    conn.request("POST", "/b1s/v1/Login", json.dumps(login_data), headers)
    response = conn.getresponse()
    
    print(f"\n✓ HTTP connection successful!")
    print(f"Status: {response.status} {response.reason}")
    
    body = response.read().decode('utf-8')
    print(f"Response preview: {body[:200]}...")
    
    conn.close()
    
except Exception as e:
    print(f"\n✗ HTTP connection failed: {e}")
    import traceback
    traceback.print_exc()

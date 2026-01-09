import ssl
import http.client
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

host = os.environ.get('SAP_B1S_HOST', 'fourb.vdc.services')
port = int(os.environ.get('SAP_B1S_PORT', 5588))

print(f"Testing connection to {host}:{port}")
print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")

# Test 1: Default SSL context
print("\n--- Test 1: Default SSL context ---")
try:
    ctx1 = ssl.create_default_context()
    ctx1.check_hostname = False
    ctx1.verify_mode = ssl.CERT_NONE
    conn1 = http.client.HTTPSConnection(host, port, context=ctx1, timeout=10)
    conn1.request("GET", "/b1s/v1/$metadata")
    resp1 = conn1.getresponse()
    print(f"✓ Success! Status: {resp1.status}")
    conn1.close()
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 2: With TLS 1.0 minimum
print("\n--- Test 2: TLS 1.0 minimum ---")
try:
    ctx2 = ssl.create_default_context()
    ctx2.check_hostname = False
    ctx2.verify_mode = ssl.CERT_NONE
    ctx2.minimum_version = ssl.TLSVersion.TLSv1
    conn2 = http.client.HTTPSConnection(host, port, context=ctx2, timeout=10)
    conn2.request("GET", "/b1s/v1/$metadata")
    resp2 = conn2.getresponse()
    print(f"✓ Success! Status: {resp2.status}")
    conn2.close()
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 3: With custom ciphers
print("\n--- Test 3: Custom ciphers (SECLEVEL=1) ---")
try:
    ctx3 = ssl.create_default_context()
    ctx3.check_hostname = False
    ctx3.verify_mode = ssl.CERT_NONE
    ctx3.set_ciphers('DEFAULT@SECLEVEL=1')
    conn3 = http.client.HTTPSConnection(host, port, context=ctx3, timeout=10)
    conn3.request("GET", "/b1s/v1/$metadata")
    resp3 = conn3.getresponse()
    print(f"✓ Success! Status: {resp3.status}")
    conn3.close()
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 4: With TLS 1.0 + custom ciphers
print("\n--- Test 4: TLS 1.0 + custom ciphers ---")
try:
    ctx4 = ssl.create_default_context()
    ctx4.check_hostname = False
    ctx4.verify_mode = ssl.CERT_NONE
    ctx4.minimum_version = ssl.TLSVersion.TLSv1
    ctx4.set_ciphers('DEFAULT@SECLEVEL=1')
    conn4 = http.client.HTTPSConnection(host, port, context=ctx4, timeout=10)
    conn4.request("GET", "/b1s/v1/$metadata")
    resp4 = conn4.getresponse()
    print(f"✓ Success! Status: {resp4.status}")
    conn4.close()
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 5: TLS 1.2 only
print("\n--- Test 5: TLS 1.2 only ---")
try:
    ctx5 = ssl.create_default_context()
    ctx5.check_hostname = False
    ctx5.verify_mode = ssl.CERT_NONE
    ctx5.minimum_version = ssl.TLSVersion.TLSv1_2
    conn5 = http.client.HTTPSConnection(host, port, context=ctx5, timeout=10)
    conn5.request("GET", "/b1s/v1/$metadata")
    resp5 = conn5.getresponse()
    print(f"✓ Success! Status: {resp5.status}")
    conn5.close()
except Exception as e:
    print(f"✗ Failed: {e}")

print("\n--- Testing complete ---")

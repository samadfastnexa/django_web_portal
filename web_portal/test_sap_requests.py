import requests
import os
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

load_dotenv()

host = os.environ.get('SAP_B1S_HOST', 'fourb.vdc.services')
port = int(os.environ.get('SAP_B1S_PORT', 5588))
base_url = f"https://{host}:{port}/b1s/v1"

print(f"Testing with requests library: {base_url}")

# Custom SSL adapter with legacy cipher support
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.load_default_certs()
        context.check_hostname = False
        context.verify_mode = 0  # ssl.CERT_NONE
        # Allow legacy ciphers
        context.set_ciphers('DEFAULT:@SECLEVEL=0')
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

# Test with requests
session = requests.Session()
session.mount('https://', SSLAdapter())

try:
    response = session.get(f"{base_url}/$metadata", verify=False, timeout=10)
    print(f"✓ Success! Status: {response.status_code}")
    print(f"Content length: {len(response.content)} bytes")
except Exception as e:
    print(f"✗ Failed: {e}")

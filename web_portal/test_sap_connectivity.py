import socket
import os
from dotenv import load_dotenv

load_dotenv()

host = os.environ.get('SAP_B1S_HOST', 'fourb.vdc.services')
port = int(os.environ.get('SAP_B1S_PORT', 5588))

print(f"Testing network connectivity to {host}:{port}")

try:
    # Test basic TCP connectivity
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex((host, port))
    
    if result == 0:
        print(f"✓ Port {port} is OPEN and accepting connections")
        sock.close()
    else:
        print(f"✗ Port {port} is CLOSED or not accessible (error code: {result})")
        
except socket.gaierror as e:
    print(f"✗ DNS resolution failed: {e}")
except socket.timeout:
    print(f"✗ Connection timeout - server not responding")
except Exception as e:
    print(f"✗ Connection failed: {e}")

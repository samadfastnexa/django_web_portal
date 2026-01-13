#!/usr/bin/env python
"""
Diagnostic script to test SAP B1 Service Layer connectivity and identify issues.
"""
import os
import sys
import socket
import ssl
import http.client
import json
import time

# Add parent directory to path for Django imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_socket_connection(host, port, timeout=5):
    """Test basic socket connectivity."""
    print(f"\n1. Testing socket connectivity to {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"   ✓ Socket connection successful")
            return True
        else:
            print(f"   ✗ Socket connection failed: Error {result}")
            return False
    except Exception as e:
        print(f"   ✗ Socket test failed: {e}")
        return False

def test_ssl_connection(host, port, timeout=5):
    """Test SSL/HTTPS connection."""
    print(f"\n2. Testing SSL/HTTPS connection to {host}:{port}...")
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            ssock.connect((host, port))
            print(f"   ✓ SSL connection successful")
            print(f"     Protocol: {ssock.version()}")
            print(f"     Cipher: {ssock.cipher()[0]}")
            return True
    except ssl.SSLError as e:
        print(f"   ✗ SSL error: {e}")
        return False
    except socket.timeout:
        print(f"   ✗ Connection timeout")
        return False
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return False

def test_http_request(host, port, path, timeout=10):
    """Test HTTP request to SAP."""
    print(f"\n3. Testing HTTP request to {host}:{port}{path}...")
    try:
        # Create SSL context that disables certificate verification
        context = ssl._create_unverified_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=context)
        headers = {'Accept': 'application/json'}
        
        print(f"   Sending GET request...")
        conn.request("GET", path, '', headers)
        
        response = conn.getresponse()
        response_text = response.read().decode('utf-8', errors='ignore')
        
        print(f"   ✓ Response received: Status {response.status}")
        if response_text:
            try:
                response_json = json.loads(response_text)
                print(f"     Response: {json.dumps(response_json, indent=2)[:500]}")
            except:
                print(f"     Response (raw): {response_text[:200]}")
        
        conn.close()
        return True
    except http.client.RemoteDisconnected as e:
        print(f"   ✗ Remote disconnected: {e}")
        print(f"     This usually means SAP rejected the connection")
        return False
    except ConnectionRefusedError as e:
        print(f"   ✗ Connection refused: {e}")
        return False
    except socket.timeout:
        print(f"   ✗ Connection timeout after {timeout}s")
        return False
    except Exception as e:
        print(f"   ✗ Request failed: {type(e).__name__}: {e}")
        return False

def test_login(host, port, username, password, company_db, base_path, timeout=10):
    """Test SAP login."""
    print(f"\n4. Testing SAP login...")
    print(f"   Username: {username}")
    print(f"   Company DB: {company_db}")
    
    try:
        login_data = {
            'UserName': username,
            'Password': password,
            'CompanyDB': company_db
        }
        
        # Create SSL context that disables certificate verification
        context = ssl._create_unverified_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=context)
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        print(f"   Sending login request...")
        conn.request("POST", f"{base_path}/Login", json.dumps(login_data), headers)
        
        response = conn.getresponse()
        response_text = response.read().decode('utf-8', errors='ignore')
        
        print(f"   Status: {response.status}")
        
        if response.status == 200:
            response_json = json.loads(response_text)
            session_id = response_json.get('SessionId')
            print(f"   ✓ Login successful!")
            print(f"     Session ID: {session_id[:20]}..." if session_id else "     (No session ID)")
            return True
        else:
            print(f"   ✗ Login failed with status {response.status}")
            try:
                error_json = json.loads(response_text)
                print(f"     Error: {json.dumps(error_json, indent=2)}")
            except:
                print(f"     Response: {response_text[:300]}")
            return False
        
    except http.client.RemoteDisconnected as e:
        print(f"   ✗ Remote disconnected during login: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Login test failed: {type(e).__name__}: {e}")
        return False

def load_env():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.isfile(env_path):
        print(f"Loading .env from: {env_path}")
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        os.environ[key] = value
            print("✓ .env loaded successfully\n")
        except Exception as e:
            print(f"✗ Failed to load .env: {e}\n")
    else:
        print(f"✗ .env file not found at: {env_path}\n")

def main():
    """Run all diagnostic tests."""
    print("=" * 60)
    print("SAP B1 Service Layer Connectivity Diagnostic")
    print("=" * 60)
    
    load_env()
    
    # Get configuration
    host = os.environ.get('SAP_B1S_HOST', 'fourb.vdc.services')
    port = int(os.environ.get('SAP_B1S_PORT', 5588))
    base_path = os.environ.get('SAP_B1S_BASE_PATH', '/b1s/v1')
    username = os.environ.get('SAP_USERNAME')
    password = os.environ.get('SAP_PASSWORD')
    company_db = os.environ.get('SAP_COMPANY_DB', '4B-BIO')
    
    print(f"\nConfiguration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Base Path: {base_path}")
    print(f"  Username: {username if username else '(not set)'}")
    print(f"  Password: {'*' * len(password) if password else '(not set)'}")
    print(f"  Company DB: {company_db}")
    
    # Run tests
    tests = [
        ('Socket', test_socket_connection(host, port)),
        ('SSL/HTTPS', test_ssl_connection(host, port)),
        ('HTTP Request', test_http_request(host, port, f"{base_path}/ServerVersion")),
    ]
    
    if username and password:
        tests.append(('Login', test_login(host, port, username, password, company_db, base_path)))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, result in tests:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in tests)
    
    if not all_passed:
        print("\nRecommendations:")
        print("1. Check if SAP B1 Service Layer is running on the server")
        print("2. Verify firewall rules allow access to port 5588")
        print("3. Confirm network/VPN connectivity to the SAP host")
        print("4. Check if credentials (username/password) are correct")
        print("5. Verify the company database name is correct")
        print("6. Check SAP B1 Service Layer logs for connection errors")
    else:
        print("\n✓ All connectivity tests passed!")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())

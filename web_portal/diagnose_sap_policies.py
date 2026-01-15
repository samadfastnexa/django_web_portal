"""
Diagnostic script for SAP policies connection issue.
This will help identify the root cause of the timeout.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
django.setup()

from sap_integration.sap_client import SAPClient
from preferences.models import Setting
import json
import socket
import time

def test_network_connection():
    """Test basic network connectivity to SAP server"""
    print("\n=== TESTING NETWORK CONNECTIVITY ===")
    
    try:
        # Get SAP host and port
        host = os.environ.get('SAP_B1S_HOST', 'fourbtest.vdc.services')
        port = int(os.environ.get('SAP_B1S_PORT', '50000'))
        
        print(f"Testing connection to {host}:{port}")
        
        # Test DNS resolution
        try:
            ip = socket.gethostbyname(host)
            print(f"✅ DNS Resolution successful: {host} -> {ip}")
        except socket.gaierror as e:
            print(f"❌ DNS Resolution failed: {e}")
            return False
        
        # Test socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        start_time = time.time()
        try:
            result = sock.connect_ex((host, port))
            elapsed = time.time() - start_time
            
            if result == 0:
                print(f"✅ Socket connection successful (took {elapsed:.2f}s)")
                sock.close()
                return True
            else:
                print(f"❌ Socket connection failed: error code {result}")
                return False
        except socket.timeout:
            print(f"❌ Socket connection timed out after 10 seconds")
            return False
        except Exception as e:
            print(f"❌ Socket connection failed: {e}")
            return False
        finally:
            try:
                sock.close()
            except:
                pass
                
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

def check_sap_settings():
    """Check SAP configuration in database"""
    print("\n=== CHECKING SAP CONFIGURATION ===")
    
    try:
        # Check SAP credentials
        try:
            cred_setting = Setting.objects.get(slug='sap_credential')
            cred_value = cred_setting.value
            if isinstance(cred_value, str):
                cred_value = json.loads(cred_value)
            
            username = cred_value.get('Username', 'NOT SET')
            has_password = 'Passwords' in cred_value and cred_value['Passwords']
            
            print(f"SAP Username: {username}")
            print(f"SAP Password: {'***SET***' if has_password else 'NOT SET'}")
        except Setting.DoesNotExist:
            print("❌ SAP credentials not found in database")
            print("Using environment variables...")
            username = os.environ.get('SAP_USERNAME', 'NOT SET')
            has_password = bool(os.environ.get('SAP_PASSWORD'))
            print(f"SAP Username (env): {username}")
            print(f"SAP Password (env): {'***SET***' if has_password else 'NOT SET'}")
        
        # Check company database
        try:
            db_setting = Setting.objects.get(slug='SAP_COMPANY_DB')
            db_value = db_setting.value
            if isinstance(db_value, str):
                try:
                    db_value = json.loads(db_value)
                except:
                    pass
            
            print(f"\nAvailable Company Databases:")
            if isinstance(db_value, dict):
                for key, value in db_value.items():
                    print(f"  - {key}: {value}")
            else:
                print(f"  Single value: {db_value}")
        except Setting.DoesNotExist:
            print("❌ Company database settings not found")
        
        # Check connection details
        print(f"\nConnection Details:")
        print(f"  Host: {os.environ.get('SAP_B1S_HOST', 'fourbtest.vdc.services')}")
        print(f"  Port: {os.environ.get('SAP_B1S_PORT', '50000')}")
        print(f"  Base Path: {os.environ.get('SAP_B1S_BASE_PATH', '/b1s/v1')}")
        print(f"  Use HTTP: {os.environ.get('SAP_USE_HTTP', 'false')}")
        
        return True
    except Exception as e:
        print(f"❌ Error checking settings: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sap_login():
    """Test SAP login"""
    print("\n=== TESTING SAP LOGIN ===")
    
    try:
        print("Attempting to create SAP client...")
        client = SAPClient(company_db_key='4B-BIO')
        
        print("Attempting to get session ID (this will trigger login)...")
        session_id = client.get_session_id()
        
        if session_id:
            print(f"✅ SAP Login successful! Session ID: {session_id[:20]}...")
            return True
        else:
            print("❌ SAP Login failed: No session ID returned")
            return False
            
    except Exception as e:
        print(f"❌ SAP Login failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_get_projects():
    """Test fetching projects (used by get_all_policies)"""
    print("\n=== TESTING GET PROJECTS ===")
    
    try:
        print("Creating SAP client...")
        client = SAPClient(company_db_key='4B-BIO')
        
        print("Fetching projects with timeout monitoring...")
        start_time = time.time()
        
        try:
            projects = client.get_projects(select="Code,Name,Active,U_pol")
            elapsed = time.time() - start_time
            
            print(f"✅ Successfully fetched {len(projects)} projects in {elapsed:.2f}s")
            
            # Show first few projects
            print("\nFirst 3 projects:")
            for i, proj in enumerate(projects[:3]):
                print(f"  {i+1}. Code: {proj.get('Code')}, Name: {proj.get('Name')}, Policy: {proj.get('U_pol')}")
            
            return True
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ Failed to fetch projects after {elapsed:.2f}s: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("SAP POLICIES CONNECTION DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # Test 1: Network connectivity
    network_ok = test_network_connection()
    
    # Test 2: Configuration
    config_ok = check_sap_settings()
    
    if not network_ok:
        print("\n" + "=" * 60)
        print("DIAGNOSIS: Network connectivity issue")
        print("=" * 60)
        print("\nThe SAP server is not reachable. Please check:")
        print("  1. Is the SAP server running?")
        print("  2. Is there a firewall blocking the connection?")
        print("  3. Is the host/port correct?")
        print("  4. Are you connected to the correct network/VPN?")
        return
    
    # Test 3: SAP Login
    login_ok = test_sap_login()
    
    if not login_ok:
        print("\n" + "=" * 60)
        print("DIAGNOSIS: SAP authentication issue")
        print("=" * 60)
        print("\nCannot login to SAP. Please check:")
        print("  1. Are the credentials correct?")
        print("  2. Is the company database name correct?")
        print("  3. Does the user have proper permissions?")
        return
    
    # Test 4: Get Projects
    projects_ok = test_get_projects()
    
    if projects_ok:
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe SAP connection is working correctly.")
        print("If you're still experiencing issues with the API,")
        print("please check the API endpoint configuration.")
    else:
        print("\n" + "=" * 60)
        print("DIAGNOSIS: Projects API issue")
        print("=" * 60)
        print("\nCan login but cannot fetch projects. Please check:")
        print("  1. Does the user have permissions to access Projects?")
        print("  2. Is the Projects service available in SAP?")
        print("  3. Are there network stability issues?")

if __name__ == '__main__':
    main()

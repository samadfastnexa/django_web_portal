#!/usr/bin/env python
"""
Script to check if a Business Partner exists in SAP Service Layer.
Uses the Django project's SAPClient for authentication and connection.

Usage:
  python sap_check_cardcode.py --card-code BIC01563 --company-db "4B-BIO_APP_"
"""
import os
import sys
import argparse
import django
import json

# Setup Django environment to allow importing SAPClient
# Assumes this script is in the project root (same as manage.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_portal.settings')
try:
    django.setup()
except Exception as e:
    print(f"Warning: Django setup failed ({e}). Attempting to continue if dependencies allow...")

try:
    from sap_integration.sap_client import SAPClient
except ImportError:
    print("Error: Could not import SAPClient. Make sure you are in the correct directory.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Check if a Business Partner exists in SAP Service Layer')
    parser.add_argument('--card-code', required=True, help='CardCode to check (e.g., BIC01563)')
    
    # Optional overrides
    parser.add_argument('--host', help='SAP Host')
    parser.add_argument('--port', help='SAP Port')
    parser.add_argument('--base-path', help='SAP Base Path (e.g. /b1s/v1)')
    parser.add_argument('--username', help='SAP Username')
    parser.add_argument('--password', help='SAP Password')
    parser.add_argument('--company-db', help='SAP Company DB')
    parser.add_argument('--post', action='store_true', help='Attempt to create the BP if it does not exist')
    parser.add_argument('--file', help='Path to JSON payload file for creation (optional)')

    args = parser.parse_args()

    # Apply overrides to environment variables so SAPClient picks them up.
    # SAPClient prioritizes os.environ over Django settings.
    if args.host:
        os.environ['SAP_B1S_HOST'] = args.host
    if args.port:
        os.environ['SAP_B1S_PORT'] = str(args.port)
    if args.base_path:
        os.environ['SAP_B1S_BASE_PATH'] = args.base_path
    if args.username:
        os.environ['SAP_USERNAME'] = args.username
    if args.password:
        os.environ['SAP_PASSWORD'] = args.password
    if args.company_db:
        # Warn if DB name looks suspicious (e.g. trailing underscore)
        if args.company_db.endswith('_'):
            print(f"Warning: Company DB '{args.company_db}' ends with an underscore. This might cause 'Switch company error'.")
            print(f"Consider using '{args.company_db.rstrip('_')}' instead.")
        os.environ['SAP_COMPANY_DB'] = args.company_db

    print('--- SAP BP Existence Check ---')
    print(f"CardCode: {args.card_code}")

    try:
        # Initialize Client
        client = SAPClient()
        
        # Test connection / Login
        print("Connecting to SAP Service Layer...")
        session_id = client.get_session_id()
        print(f"Login successful. Session ID: {session_id[:15]}...")

        # Check BP
        print(f"Querying BusinessPartners('{args.card_code}')...")
        try:
            # We use get_business_partner which does a direct GET /BusinessPartners('CardCode')
            bp = client.get_business_partner(args.card_code)
            
            print(f"✓ Found Business Partner: {args.card_code}")
            # Print some key details
            summary = {
                "CardCode": bp.get("CardCode"),
                "CardName": bp.get("CardName"),
                "CardType": bp.get("CardType"),
                "CurrentAccountBalance": bp.get("CurrentAccountBalance")
            }
            print(json.dumps(summary, indent=2))
            
        except Exception as e:
            # Check if it's a 404 Not Found wrapped in an exception
            err_str = str(e)
            if "Not Found" in err_str or "not found" in err_str or "404" in err_str:
                 print(f"✗ Business Partner '{args.card_code}' does NOT exist.")
                 
                 if args.post:
                      print(f"\n--- Attempting to CREATE Business Partner '{args.card_code}' ---")
                      
                      payload = {}
                      if args.file:
                          try:
                              with open(args.file, 'r', encoding='utf-8') as f:
                                  payload = json.load(f)
                              print(f"Loaded payload from {args.file}")
                          except Exception as fe:
                              print(f"✗ Failed to load payload file: {fe}")
                              sys.exit(1)
                      else:
                          # Template payload based on existing patterns
                          payload = {
                             "CardCode": args.card_code,
                             "CardName": f"Test Partner {args.card_code}",
                             "CardType": "cCustomer",
                             "GroupCode": 100,
                             "Series": 70, 
                             "Address": "Test Address via Script",
                             "Phone1": "03001234567",
                             "FederalTaxID": "00000-0000000-0",
                             "Currency": "##" # All currencies
                          }
                      
                      # Ensure CardCode in payload matches argument if not explicitly set in file (or override it?)
                      if not payload.get('CardCode'):
                          payload['CardCode'] = args.card_code

                      print("Payload:")
                      print(json.dumps(payload, indent=2))
                      try:
                          new_bp = client.create_business_partner(payload)
                          created_code = new_bp.get('CardCode')
                          print(f"✓ Successfully created BP {created_code}")
                          if created_code != args.card_code:
                              print(f"  (Note: Requested {args.card_code}, but SAP assigned {created_code})")
                          
                          # Print summary of created BP
                          summary = {
                                "CardCode": new_bp.get("CardCode"),
                                "CardName": new_bp.get("CardName"),
                                "CardType": new_bp.get("CardType"),
                                "CurrentAccountBalance": new_bp.get("CurrentAccountBalance")
                          }
                          print(json.dumps(summary, indent=2))
                          sys.exit(0)
                      except Exception as create_err:
                          print(f"✗ Failed to create BP: {create_err}")
                          sys.exit(1)
            else:
                 print(f"✗ Error fetching BP: {e}")
                 if "Switch company error" in err_str:
                     print("  Hint: Verify the --company-db value. It might be incorrect.")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Fatal Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

#!/usr/bin/env python
"""
Quick script to test HANA connection for FOURB-PROD using dedicated env vars.

FOURB-PROD SAP HANA Credentials (Built-in defaults):
  DB Server: 192.168.16.6
  System ID: NDB
  Port: 30015
  User: SYSTEM
  Password: S@pHFP21*
  Schema: 4B-ORANG_APP
  Control Center: https://192.168.16.6:40000/ControlCenter/

Usage:
  # Quick test with built-in defaults
  python check_hana_fourb_prod.py
  
  # With custom timeout and retries
  python check_hana_fourb_prod.py --timeout 300 --retries 3
  
  # Override credentials
  python check_hana_fourb_prod.py --host <host> --user <user> --password <pass>
  
  # Or use environment variables to override defaults
  set HANA_PROD_HOST=...
  set HANA_PROD_PORT=30015
  set HANA_PROD_USER=...
  set HANA_PROD_PASSWORD=...
  set HANA_PROD_SCHEMA=4B-ORANG_APP
"""
import os
import sys
from pathlib import Path
import argparse
import getpass
try:
    from dotenv import load_dotenv  # optional
except Exception:
    load_dotenv = None


def main() -> int:
    try:
        from hdbcli import dbapi
    except Exception as e:
        print("✗ hdbcli not installed or import failed:", e)
        return 1

    # CLI args (override env if provided)
    parser = argparse.ArgumentParser(description="FOURB-PROD HANA connection check")
    parser.add_argument("--host", dest="host")
    parser.add_argument("--port", dest="port", type=int)
    parser.add_argument("--user", dest="user")
    parser.add_argument("--password", dest="password")
    parser.add_argument("--schema", dest="schema")
    parser.add_argument("--timeout", dest="timeout", type=int, default=120, help="Connection timeout in seconds (default: 120)")
    parser.add_argument("--encrypt", dest="encrypt", action="store_true", help="Enable TLS/SSL for HANA connection")
    parser.add_argument("--ssl-validate", dest="ssl_validate", action="store_true", help="Validate server certificate when encrypting")
    parser.add_argument("--retries", dest="retries", type=int, default=1, help="Number of connection retry attempts (default: 1)")
    args = parser.parse_args()

    # Try to load env files if python-dotenv is available
    if load_dotenv:
        base = Path(__file__).resolve().parent
        for p in [
            base / ".env.fourb_prod",
            base / ".env.prod",
            base / ".env",
            base.parent / ".env",
        ]:
            try:
                load_dotenv(dotenv_path=str(p), override=False)
            except Exception:
                pass

    # FOURB-PROD Default Credentials (can be overridden by args or env vars)
    DEFAULT_FOURB_HOST = "192.168.16.6"
    DEFAULT_FOURB_PORT = 30015
    DEFAULT_FOURB_USER = "SYSTEM"
    DEFAULT_FOURB_PASSWORD = "S@pHFP21*"
    DEFAULT_FOURB_SCHEMA = "4B-ORANG_APP"
    
    host = (args.host or os.environ.get("HANA_PROD_HOST", DEFAULT_FOURB_HOST)).strip()
    port = int(args.port or int(os.environ.get("HANA_PROD_PORT", DEFAULT_FOURB_PORT) or DEFAULT_FOURB_PORT))
    user = (args.user or os.environ.get("HANA_PROD_USER", DEFAULT_FOURB_USER)).strip()
    password = (args.password or os.environ.get("HANA_PROD_PASSWORD", DEFAULT_FOURB_PASSWORD)).strip()
    schema = (args.schema or os.environ.get("HANA_PROD_SCHEMA", DEFAULT_FOURB_SCHEMA)).strip()

    print("=" * 60)
    print("FOURB-PROD HANA CONNECTION CHECK")
    print("=" * 60)
    print(f"System ID: NDB")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")
    print(f"Schema: {schema or '(not specified)'}")
    print(f"Timeout: {args.timeout} seconds")
    print(f"Retries: {args.retries}")
    print(f"Encryption: {'Enabled' if args.encrypt else 'Disabled'}")
    print(f"Control Center: https://{host}:40000/ControlCenter/")

    import time
    
    for attempt in range(1, args.retries + 1):
        try:
            if args.retries > 1:
                print(f"\n[Attempt {attempt}/{args.retries}]")
            
            print(f"Connecting to {host}:{port} as {user}...")
            print(f"Timeout set to {args.timeout} seconds...")
            
            start_time = time.time()
            kwargs = {
                "address": host, 
                "port": port, 
                "user": user, 
                "password": password,
                "connectTimeout": args.timeout * 1000  # HANA expects milliseconds
            }
            if args.encrypt:
                kwargs["encrypt"] = True
                kwargs["sslValidateCertificate"] = bool(args.ssl_validate)
                print("Using encrypted connection...")
            
            conn = dbapi.connect(**kwargs)
            connection_time = time.time() - start_time
            print(f"✓ Connected successfully in {connection_time:.2f} seconds")
            
            cur = conn.cursor()
            if schema:
                print(f"Setting schema to {schema}...")
                cur.execute(f'SET SCHEMA "{schema}"')
            
            print("Executing test query...")
            cur.execute("SELECT CURRENT_UTCTIMESTAMP AS TS FROM DUMMY")
            row = cur.fetchone()
            print(f"✓ Query executed successfully")
            print(f"✓ CURRENT_UTCTIMESTAMP: {row[0] if row else 'N/A'}")
            
            cur.close()
            conn.close()
            print("\n" + "=" * 60)
            print("✓ FOURB-PROD HANA CONNECTION TEST SUCCEEDED")
            print("=" * 60)
            return 0
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n✗ Connection attempt {attempt} failed after {elapsed:.2f} seconds")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {e}")
            
            if attempt < args.retries:
                wait_time = min(5 * attempt, 15)  # Progressive backoff, max 15 seconds
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print("\n" + "=" * 60)
                print("✗ ALL CONNECTION ATTEMPTS FAILED")
                print("=" * 60)
                print("\nTroubleshooting tips:")
                print("1. Verify HANA server is running and accessible")
                print("2. Check firewall rules allow connection to port", port)
                print("3. Verify credentials are correct")
                print("4. Try increasing timeout: --timeout 300")
                print("5. Check if VPN connection is required")
                print("6. Try with encryption: --encrypt")
                return 1


if __name__ == "__main__":
    raise SystemExit(main())

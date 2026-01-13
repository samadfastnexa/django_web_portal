# Quick Test Commands

## 1. Run the Diagnostic Tool
```powershell
cd "f:\samad\clone tarzan\django_web_portal\web_portal"
.\.venv\Scripts\activate
python diagnose_sap_bp_error.py
```

## 2. Check SAP Configuration
```powershell
python check_sap_config.py
```

## 3. Test Django Server
```powershell
python manage.py runserver
```
Then visit: http://localhost:8000/admin/sap-bp-entry/

## 4. Manual Quick Test in Python
```python
import os
import sys
import django

# Setup
sys.path.insert(0, r'f:\samad\clone tarzan\django_web_portal\web_portal')
os.environ['DJANGO_SETTINGS_MODULE'] = 'web_portal.settings'

# Load .env
from pathlib import Path
env_path = Path(r'f:\samad\clone tarzan\django_web_portal\.env')
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

django.setup()

# Test
from sap_integration.sap_client import SAPClient

client = SAPClient()
print(f"Company DB: {client.company_db}")
print(f"Username: {client.username}")
print(f"Host: {client.host}:{client.port}")

# Test login
session_id = client.get_session_id()
print(f"Session ID: {session_id}")
print("✓ Login successful!")

# Test minimal BP creation
payload = {
    "CardName": "TEST FROM PYTHON",
    "CardType": "cCustomer",
    "GroupCode": 100
}
result = client.create_business_partner(payload)
print(f"✓ BP Created: {result}")
```

## Expected Output

### If Configuration is Correct:
```
Company DB: 4B-BIO_APP
Username: Fast01
Host: fourbtest.vdc.services:50000
Session ID: <some-uuid>
✓ Login successful!
```

### If Company DB is Wrong:
You'll still see a session ID, but BP creation will fail with:
```
SAP error 400: { "error" : { "code" : "-1", "message" : "Failed to initialize object data" } }
```

## Key Things to Verify

1. **Company DB** must be `4B-BIO_APP` (not 4B-ORANG_APP)
2. **Username** must be `Fast01` (case-sensitive)
3. **Session ID** should be returned successfully
4. **Port** should be `50000` for Service Layer (not 30015)

## If Still Failing

Check these in SAP B1 Admin:
1. Does user 'Fast01' have BusinessPartner creation rights?
2. Does Series=70 exist in BP numbering series?
3. Does GroupCode=100 exist in BP groups?
4. Does Territory=235 exist in territories?
5. Are all UDF fields defined (U_leg, U_gov, etc.)?

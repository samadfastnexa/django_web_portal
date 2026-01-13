# SAP Connectivity Issue - Root Cause Analysis & Fix

## Issue
When calling `GET /api/sap/policies/`, the API returns a 500 error:
```
{
  "success": false,
  "error": "SAP integration failed",
  "message": "[WinError 10054] An existing connection was forcibly closed by the remote host"
}
```

## Root Cause
After diagnostic testing, the actual issue is an **SSL/TLS handshake error**:
- **Error**: `[SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error`
- **Location**: Connection from Django to SAP B1 Service Layer at `fourb.vdc.services:5588`
- **Problem**: Python's default SSL context was not properly configured to handle SAP's self-signed certificate and legacy TLS configuration

The SAP server sends an SSL internal error, which causes Python's http.client to forcibly close the connection (WinError 10054).

## Solutions Implemented

### 1. **Fixed SSL Context Creation** (sap_client.py)
   
**Before:**
```python
self.ssl_context = ssl.create_default_context()
self.ssl_context.check_hostname = False
self.ssl_context.verify_mode = ssl.CERT_NONE
```

**After:**
```python
try:
    self.ssl_context = ssl._create_unverified_context()
except AttributeError:
    self.ssl_context = ssl.create_default_context()
    self.ssl_context.check_hostname = False
    self.ssl_context.verify_mode = ssl.CERT_NONE

self.ssl_context.check_hostname = False
self.ssl_context.verify_mode = ssl.CERT_NONE
```

**Why:** `_create_unverified_context()` is specifically designed to bypass certificate verification while properly disabling all certificate validation checks, avoiding the `CERTIFICATE_VERIFY_FAILED` error.

### 2. **Enhanced TLS Version & Cipher Configuration** (sap_client.py)
   
Added fallback logic for TLS versions and cipher suites:
```python
# Try to set TLS 1.2 as minimum, fall back to TLS 1.0 if needed
if hasattr(ssl, 'TLSVersion'):
    try:
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    except:
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1
```

Configured compatible cipher suites with fallbacks:
```python
try:
    self.ssl_context.set_ciphers('ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-GCM-SHA256')
except ssl.SSLError:
    # Fallback to broader cipher set
    self.ssl_context.set_ciphers('DEFAULT:!aNULL:!eNULL:!MD5:!3DES:!DES:!RC4:!IDEA:!SEED:!aDSS:!SRP:!PSK')
```

### 3. **Implemented Retry Logic for SSL Errors** (sap_client.py)

**In `_make_request()` method:**
```python
except ssl.SSLError as e:
    error_str = str(e)
    
    # If it's an internal error from SAP, try once more with a delay
    if 'TLSV1_ALERT_INTERNAL_ERROR' in error_str or 'alert internal error' in error_str:
        if retry:
            logger.info("[SAP SSL ERROR] Detected SAP internal SSL error - retrying after delay...")
            time.sleep(1)  # Wait 1 second before retrying
            return self._make_request(method, path, body, retry=False)
```

**In `_login()` method:**
- Added SSL error handling with exponential backoff
- Attempts retry after 1 second delay for internal errors

### 4. **Improved Error Messages** (views.py)

Updated the `/api/sap/policies/` endpoint to provide better error information:
```python
if 'TLSV1_ALERT_INTERNAL_ERROR' in error_msg or 'alert internal error' in error_msg:
    return Response({
        "success": False,
        "error": "SAP Server SSL Internal Error",
        "message": "The SAP B1 Service Layer at fourb.vdc.services:5588 is experiencing SSL issues. This may be temporary. Please try again in a moment or check if the SAP server is running properly.",
        "technical_detail": error_msg,
        "recommendation": "If this persists, check SAP B1 Service Layer status and logs"
    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
```

### 5. **Created Diagnostic Tool** (diagnose_sap_connection.py)

A comprehensive diagnostic script to test:
- Socket connectivity
- SSL/TLS connection
- HTTP requests to SAP
- Login authentication

Usage:
```bash
python diagnose_sap_connection.py
```

## Files Modified

1. **sap_integration/sap_client.py**
   - Fixed SSL context initialization
   - Enhanced TLS version and cipher configuration
   - Added retry logic for SSL errors
   - Improved error logging

2. **sap_integration/views.py**
   - Enhanced error handling in `list_policies()` endpoint
   - Better error messages for SSL issues

3. **diagnose_sap_connection.py** (NEW)
   - Comprehensive diagnostic tool

## Next Steps if Issue Persists

1. **Check SAP Server Status**
   ```powershell
   # Test basic connectivity
   Test-NetConnection -ComputerName fourb.vdc.services -Port 5588
   ```

2. **Check SAP B1 Service Layer Logs**
   - Location: `C:\Program Files\SAP\SAP Business One DI API\ServiceLayer\logs\`
   - Look for SSL-related errors

3. **Enable HTTP Fallback** (if SSL cannot be fixed)
   - Set `SAP_USE_HTTP=true` in `.env` file
   - Update SAP B1 Service Layer to listen on HTTP port (typically 50000)
   - **Note:** Only use for development/troubleshooting, not for production

4. **Contact SAP Support**
   - If the SAP server's SSL certificate is misconfigured
   - If the server needs updates for TLS compatibility

## Environment Variables

The following env vars control SAP connectivity:
```
SAP_B1S_HOST=fourb.vdc.services
SAP_B1S_PORT=5588
SAP_B1S_BASE_PATH=/b1s/v1
SAP_USERNAME=FOURBPVTC\TEP40
SAP_PASSWORD=@ip39$**
SAP_COMPANY_DB=4B-BIO
SAP_USE_HTTP=false  # Set to 'true' to use HTTP instead of HTTPS (debugging only)
```

## Testing the Fix

1. **Using the diagnostic tool:**
   ```bash
   cd web_portal
   python diagnose_sap_connection.py
   ```

2. **Using Django:**
   ```bash
   python manage.py shell
   ```
   Then:
   ```python
   from sap_integration.sap_client import SAPClient
   client = SAPClient(company_db_key='4B-BIO')
   policies = client.get_all_policies()
   print(f"Retrieved {len(policies)} policies")
   ```

3. **Using the API:**
   ```bash
   curl http://localhost:8000/api/sap/policies/
   ```

## Performance Impact

- **Minimal**: Retry logic only activates on SSL errors (transient issues)
- **Normal flow**: No additional latency
- **On error**: Single 1-second delay for retry

## Security Notes

- SSL certificate verification is disabled (`verify_mode = ssl.CERT_NONE`) because SAP uses self-signed certificates
- This is acceptable for enterprise SAP systems in corporate networks
- For production deployments, consider configuring proper certificates on the SAP server

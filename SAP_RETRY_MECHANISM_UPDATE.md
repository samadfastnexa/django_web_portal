# SAP SSL Error - Enhanced Retry Mechanism

## Issue Update

The API is now correctly returning a **503 Service Unavailable** error with a clear message indicating the SAP B1 Service Layer is experiencing SSL issues. This is an improvement from the previous cryptic 500 error.

**Current Response:**
```json
{
  "success": false,
  "error": "SAP Server SSL Internal Error",
  "message": "The SAP B1 Service Layer at fourb.vdc.services:5588 is experiencing SSL issues...",
  "technical_detail": "[SSL: TLSV1_ALERT_INTERNAL_ERROR] tlsv1 alert internal error",
  "recommendation": "If this persists, check SAP B1 Service Layer status and logs"
}
```

## Problem Analysis

The SAP B1 Service Layer server itself is experiencing SSL/TLS handshake problems. This is a **server-side issue**, not a client configuration issue. The server is sending `TLSV1_ALERT_INTERNAL_ERROR`, which indicates:

1. **Possible Causes:**
   - SAP B1 Service Layer is overloaded or restarting
   - SSL/TLS configuration issue on the SAP server
   - SAP Service Layer process is not fully ready
   - Network connectivity fluctuations during handshake

## Solution: Enhanced Retry Mechanism

To handle transient SAP SSL issues, we've implemented an **aggressive exponential backoff retry strategy** with multiple retry attempts.

### How It Works

**Before:** Single retry with 1-second delay
**Now:** Up to 3 total attempts with exponential backoff:
- **Attempt 1:** Immediate
- **Attempt 2:** After 1 second delay
- **Attempt 3:** After 2 second delay
- **Failure:** Returns 503 with helpful message

### Retry Flow

```
GET /api/sap/policies/
        ↓
_make_request(attempt=0)
        ↓
SSL Error Detected
        ↓
Is it TLSV1_ALERT_INTERNAL_ERROR? 
        ├─ YES → attempt < max_retries? 
        │         ├─ YES → Wait 2^attempt seconds, retry
        │         └─ NO → Return 503 with message
        └─ NO → Return SSL error immediately
```

### Code Changes

#### In `_make_request()` method:
```python
def _make_request(self, method, path, body='', retry=True, attempt=0, max_ssl_retries=3):
    # ... existing code ...
    
    except ssl.SSLError as e:
        if 'TLSV1_ALERT_INTERNAL_ERROR' in error_str or 'alert internal error' in error_str:
            if attempt < max_ssl_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                logger.info(f"[SAP SSL ERROR] Retrying in {wait_time}s (attempt {attempt + 1}/{max_ssl_retries})")
                time.sleep(wait_time)
                # Increment attempt and retry
                return self._make_request(method, path, body, retry=True, attempt=attempt + 1, max_ssl_retries=max_ssl_retries)
            else:
                # Max retries reached
                raise Exception("SAP Server SSL Internal Error - Max retries reached...")
```

#### In `_login()` method:
```python
except ssl.SSLError as ssl_err:
    if 'TLSV1_ALERT_INTERNAL_ERROR' in error_str:
        max_retries = 3
        for attempt in range(1, max_retries):
            wait_time = 2 ** (attempt - 1)  # 1s, 2s
            logger.info(f"[SAP LOGIN] SSL error - retrying in {wait_time}s (attempt {attempt}/{max_retries})")
            time.sleep(wait_time)
            try:
                return do_login(login_data, self.base_path)
            except ssl.SSLError:
                if attempt == max_retries - 1:
                    raise Exception("SAP Server SSL Internal Error - Max retries reached...")
```

## Retry Timing

| Attempt | Event | Delay | Total Wait |
|---------|-------|-------|-----------|
| 1 | Initial request | - | 0s |
| 2 | SSL error, exponential backoff | 2^0 = 1s | 1s |
| 3 | SSL error, exponential backoff | 2^1 = 2s | 3s |
| 4 | All retries exhausted | - | Give up, return 503 |

**Total maximum wait time: 3 seconds** before returning error to client.

## Benefits

✅ **Handles Transient Issues:** If SAP is briefly restarting or overloaded, the retry will succeed
✅ **Exponential Backoff:** Avoids hammering the server while it's recovering
✅ **User-Friendly:** Returns clear error message after all retries are exhausted
✅ **Transparent:** No changes needed to client code - retries happen automatically
✅ **Logging:** Detailed logs show retry attempts for debugging

## What To Do When You See 503 Error

### Step 1: Check SAP B1 Service Layer Status
```powershell
# Check if port is responding
Test-NetConnection -ComputerName fourb.vdc.services -Port 5588 -InformationLevel Detailed

# Check if service is running (on SAP server)
Get-Service -Name "*B1*" -ErrorAction SilentlyContinue
Get-Process -Name "*ServiceLayer*" -ErrorAction SilentlyContinue
```

### Step 2: Retry the Request
The system has already retried 3 times automatically. If you still get 503:
- **Wait a few seconds** and retry manually
- The issue is likely SAP server-side and self-healing

### Step 3: Check SAP Server Logs
```
On SAP Server:
C:\Program Files\SAP\SAP Business One DI API\ServiceLayer\logs\
Look for SSL or connection-related errors
```

### Step 4: Restart SAP B1 Service Layer (if needed)
```powershell
# On SAP Server (Administrator)
Stop-Service "SAP Business One DI API Service Layer" -Force
Start-Service "SAP Business One DI API Service Layer"
```

### Step 5: Contact SAP Support
If SSL errors persist, contact your SAP administrator to:
- Check SAP B1 Service Layer logs
- Verify SSL certificate configuration
- Check system resources (CPU, memory, disk space)
- Review SAP B1 installation for issues

## Monitoring & Debugging

### Check Logs for Retry Attempts
```bash
# In Django logs, look for:
[SAP SSL ERROR - Attempt 1/3]
[SAP SSL ERROR - Attempt 2/3]
[SAP SSL ERROR] Max retries (3) reached. Giving up.
```

### Manual Testing
```bash
# Test SAP connectivity directly
cd web_portal
python diagnose_sap_connection.py

# Expected output should show:
# ✓ Socket connection successful
# ✓ SSL/HTTPS connection successful  
# ✓ HTTP request successful (after retry)
# ✓ Login successful
```

## When This Helps vs When It Doesn't

### ✅ Helps With:
- SAP service temporarily restarting (recovers within 1-2 seconds)
- Brief CPU/memory spike causing timeouts (recovers quickly)
- Network hiccups during handshake (resolves on retry)
- SSL session pool exhaustion (recovers with delay)

### ❌ Doesn't Help With:
- Persistent SAP service crashes (need manual restart)
- Network connectivity broken (need IT/Network team)
- SSL certificate corruption (need certificate replacement)
- Firewall/routing issues (need infrastructure team)

## Files Modified

- **sap_integration/sap_client.py**
  - Enhanced `_make_request()` with retry attempt tracking
  - Exponential backoff calculation (2^attempt)
  - Better error logging with attempt numbers
  - Enhanced `_login()` with similar retry logic

## Next Steps if Error Persists

1. **Increase retry attempts** (if server needs more time to recover):
   ```python
   max_ssl_retries=5  # Change from 3 to 5
   ```

2. **Check SAP server health:**
   - Disk space: `dir C:\`
   - Memory: `Get-Process | Select Name, WorkingSet | Sort WorkingSet -Desc`
   - CPU: `Get-Counter '\Processor(_Total)\% Processor Time'`

3. **Enable HTTP fallback** (temporary debugging only):
   ```
   SAP_USE_HTTP=true
   SAP_B1S_PORT=50000
   ```
   
   **Warning:** This requires SAP server to be configured for HTTP and is not secure.

4. **Escalate to SAP Support** with:
   - Full error message and technical details
   - Django application logs
   - SAP B1 Service Layer logs
   - System information (CPU, memory, disk usage)

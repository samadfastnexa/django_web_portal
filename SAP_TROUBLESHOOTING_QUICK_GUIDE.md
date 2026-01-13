# Quick SAP Troubleshooting Guide

## Symptom: `[WinError 10054] Connection forcibly closed` or SSL Error

### Quick Diagnosis
```bash
cd web_portal
python diagnose_sap_connection.py
```

### Common Issues & Solutions

#### 1. SSL Error: `TLSV1_ALERT_INTERNAL_ERROR`
**Cause:** SAP B1 Service Layer is having SSL issues (usually temporary)

**Solutions:**
- Wait a few seconds and retry the request
- Check if SAP B1 Service Layer is running
- Restart SAP B1 Service Layer if needed
- Check SAP logs for details

#### 2. Connection Refused
**Cause:** Port 5588 is not accessible or SAP is not running

**Solutions:**
```powershell
# Check if port is open
Test-NetConnection -ComputerName fourb.vdc.services -Port 5588

# If closed, SAP B1 Service Layer is not running or firewall is blocking
```

#### 3. Certificate Verification Failed
**Cause:** Python SSL configuration issue

**Solutions:**
- The fix already handles this by using `ssl._create_unverified_context()`
- If still getting errors, the SAP certificate may be corrupt
- Contact SAP server admin

#### 4. Authentication Failed (Login Status 401/403)
**Cause:** Invalid credentials

**Solutions:**
- Verify `SAP_USERNAME` and `SAP_PASSWORD` in `.env`
- Check `SAP_COMPANY_DB` value is correct
- Ensure user has access to the database

### Testing Steps

1. **Test connectivity:**
   ```bash
   python diagnose_sap_connection.py
   ```

2. **Test from Django shell:**
   ```bash
   python manage.py shell
   ```
   ```python
   from sap_integration.sap_client import SAPClient
   try:
       client = SAPClient(company_db_key='4B-BIO')
       session = client.get_session_id()
       print(f"✓ Login successful. Session: {session[:30]}...")
   except Exception as e:
       print(f"✗ Error: {e}")
   ```

3. **Test policies API:**
   ```bash
   curl "http://localhost:8000/api/sap/policies/"
   ```

### Key Environment Variables

```bash
# Required
SAP_B1S_HOST=fourb.vdc.services
SAP_B1S_PORT=5588
SAP_USERNAME=FOURBPVTC\TEP40
SAP_PASSWORD=@ip39$**
SAP_COMPANY_DB=4B-BIO

# Optional (for debugging)
SAP_USE_HTTP=false  # Set to 'true' for HTTP instead of HTTPS
```

### Retry Behavior

The system automatically retries once if:
- SSL internal error is detected → waits 1 second before retry
- Session timeout occurs → forces re-login
- Cache refresh failure → forces re-login

No manual retry needed - just call the API again!

### Logs Location

For debugging, check logs:
```bash
# Django logs (if configured)
tail -f logs/django.log

# SAP B1 Service Layer logs (on SAP server)
C:\Program Files\SAP\SAP Business One DI API\ServiceLayer\logs\
```

### Emergency: HTTP Fallback

If SSL continues to fail:

1. Add to `.env`:
   ```
   SAP_USE_HTTP=true
   SAP_B1S_PORT=50000
   ```

2. Configure SAP B1 Service Layer to listen on port 50000 HTTP (consult SAP admin)

3. **WARNING:** This is insecure - use only for development/troubleshooting

### When to Contact Support

- SAP server SSL certificate appears to be misconfigured
- Persistent `TLSV1_ALERT_INTERNAL_ERROR` after multiple retries
- Connection works sometimes but fails intermittently (likely SAP load balancer issue)
- Network connectivity is uncertain

Contact: SAP Server Administrator / Network Team

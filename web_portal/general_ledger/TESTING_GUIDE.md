# General Ledger - Testing Guide

## Quick Start

### 1. Check Installation

```bash
# Navigate to project directory
cd F:\samad\clone tarzan\django_web_portal\web_portal

# Activate virtual environment
.\.venv\Scripts\activate

# Verify the app is registered
python manage.py check
```

Expected output: `System check identified no issues`

### 2. Run Migrations (if any)

```bash
python manage.py makemigrations general_ledger
python manage.py migrate
```

### 3. Start Development Server

```bash
python manage.py runserver
```

## Testing Admin Interface

### Access the Admin Page

1. Open browser: `http://localhost:8000/admin/general-ledger/`
2. Login with staff credentials
3. You should see:
   - Company Database Selector (purple gradient card)
   - Report Filters form
   - Empty state message

### Apply Filters and View Data

1. **Select Company**: Choose `4B-BIO` or `4B-ORANG` from dropdown
2. **Set Date Range**: 
   - From Date: `2024-01-01`
   - To Date: `2024-12-31`
3. **Optional Filters**:
   - Account From: Select any account (e.g., `11010100`)
   - Account To: Select any account
   - Business Partner: Leave blank for all
4. Click **"Apply Filters"**
5. View Results:
   - Account headers (blue gradient)
   - Opening balance rows (yellow)
   - Transaction rows
   - Subtotal rows (blue)
   - Grand total row (purple)

### Export to CSV

1. Apply filters to get data
2. Click **"📥 Export CSV"** button
3. CSV file will download automatically
4. Open in Excel to verify

## Testing REST API

### Using Browser

1. Open: `http://localhost:8000/swagger/`
2. Find "General Ledger" tag
3. Expand `GET /api/general-ledger/`
4. Click "Try it out"
5. Fill parameters:
   - company: `4B-BIO`
   - from_date: `2024-01-01`
   - to_date: `2024-12-31`
   - group_by_account: `true`
6. Click "Execute"
7. View Response

### Using cURL

```bash
# Get Ledger (Flat)
curl "http://localhost:8000/api/general-ledger/?company=4B-BIO&from_date=2024-01-01&to_date=2024-12-31"

# Get Ledger (Grouped)
curl "http://localhost:8000/api/general-ledger/?company=4B-BIO&from_date=2024-01-01&to_date=2024-12-31&group_by_account=true"

# Get Chart of Accounts
curl "http://localhost:8000/api/chart-of-accounts/?company=4B-BIO"

# Get Transaction Types
curl "http://localhost:8000/api/transaction-types/"

# Get Business Partners
curl "http://localhost:8000/api/business-partners/?company=4B-BIO"

# Get Projects
curl "http://localhost:8000/api/projects/?company=4B-BIO"
```

### Using Postman

1. Create new request
2. Method: `GET`
3. URL: `http://localhost:8000/api/general-ledger/`
4. Add Query Params:
   - `company`: `4B-BIO`
   - `from_date`: `2024-01-01`
   - `to_date`: `2024-12-31`
   - `group_by_account`: `true`
5. Send request
6. Verify JSON response

## Testing React/Mobile Integration

### Example React Component

```jsx
import React, { useState, useEffect } from 'react';

function GeneralLedgerReport() {
  const [ledgerData, setLedgerData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchLedger = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        '/api/general-ledger/?company=4B-BIO&from_date=2024-01-01&to_date=2024-12-31&group_by_account=true'
      );
      const data = await response.json();
      if (data.success) {
        setLedgerData(data.data);
      }
    } catch (error) {
      console.error('Error fetching ledger:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!ledgerData) return <div>No data</div>;

  return (
    <div>
      <h2>General Ledger</h2>
      {ledgerData.accounts.map(account => (
        <div key={account.Account}>
          <h3>{account.Account} - {account.AccountName}</h3>
          <p>Opening: {account.OpeningBalance}</p>
          <p>Debit: {account.TotalDebit}</p>
          <p>Credit: {account.TotalCredit}</p>
          <p>Closing: {account.ClosingBalance}</p>
        </div>
      ))}
      <div>
        <h3>Grand Total</h3>
        <p>Debit: {ledgerData.grand_total.TotalDebit}</p>
        <p>Credit: {ledgerData.grand_total.TotalCredit}</p>
        <p>Difference: {ledgerData.grand_total.Difference}</p>
      </div>
    </div>
  );
}

export default GeneralLedgerReport;
```

## Common Issues & Solutions

### Issue: "Module 'hdbcli' not found"

**Solution:**
```bash
pip install hdbcli
```

### Issue: "Connection refused to HANA"

**Solution:**
1. Check `.env` file has correct HANA credentials
2. Verify network connectivity:
   ```bash
   ping fourbtest.vdc.services
   ```
3. Check VPN if required

### Issue: "No data returned"

**Solution:**
1. Verify company database has data in HANA
2. Check date range - try wider range
3. Verify schema is correctly set
4. Query HANA directly to confirm data exists:
   ```sql
   SELECT COUNT(*) FROM "OJDT" WHERE "RefDate" >= '2024-01-01'
   ```

### Issue: "Page not found (404)"

**Solution:**
1. Verify URLs are registered:
   ```bash
   python manage.py show_urls | grep general
   ```
2. Check `web_portal/urls.py` includes general_ledger URLs
3. Restart Django server

### Issue: "Template not found"

**Solution:**
1. Verify template location:
   ```
   general_ledger/templates/general_ledger/general_ledger.html
   ```
2. Check `INSTALLED_APPS` includes `'general_ledger'`
3. Restart Django server

## Performance Testing

### Test with Large Date Range

```bash
# 1 year of data
curl "http://localhost:8000/api/general-ledger/?company=4B-BIO&from_date=2024-01-01&to_date=2024-12-31&page_size=100"
```

Monitor:
- Response time
- Memory usage
- Database query time

### Test Pagination

```bash
# Page 1
curl "http://localhost:8000/api/general-ledger/?company=4B-BIO&from_date=2024-01-01&to_date=2024-12-31&page=1&page_size=50"

# Page 2
curl "http://localhost:8000/api/general-ledger/?company=4B-BIO&from_date=2024-01-01&to_date=2024-12-31&page=2&page_size=50"
```

Verify:
- `pagination.total_records` is consistent
- `pagination.total_pages` is correct
- Data doesn't overlap between pages

## Validation Checklist

- [ ] Admin page loads without errors
- [ ] Company dropdown works
- [ ] All filter fields populated correctly
- [ ] Data displays grouped by account
- [ ] Opening balances shown correctly
- [ ] Running balance calculates correctly
- [ ] Subtotals match transactions
- [ ] Grand total debit = credit (balanced)
- [ ] Pagination works
- [ ] CSV export downloads
- [ ] API returns valid JSON
- [ ] Swagger docs accessible
- [ ] API pagination works
- [ ] Group by account returns correct structure
- [ ] Error handling works (invalid dates, etc.)
- [ ] Mobile API integration works

## Next Steps

1. Test with real SAP data
2. Verify calculations match SAP B1 reports
3. Performance optimization if needed
4. Add to mobile app
5. User acceptance testing

## Support

For issues or questions, contact the development team.

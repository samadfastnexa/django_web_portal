# General Ledger App

SAP Business One General Ledger reporting system for Django Web Portal.

## Features

### REST API Endpoints (for Mobile/React App)
- `GET /api/general-ledger/` - Fetch ledger transactions with filters
- `GET /api/chart-of-accounts/` - Get chart of accounts for dropdowns
- `GET /api/transaction-types/` - Get SAP B1 transaction types
- `GET /api/business-partners/` - Get business partners list
- `GET /api/projects/` - Get projects list

### Admin Web Interface
- `GET /admin/general-ledger/` - Full-featured ledger report UI
- `GET /admin/general-ledger/export-csv/` - Export ledger to CSV

## Installation

The app is already registered in `INSTALLED_APPS` in `settings.py`.

## Usage

### API Example (Mobile App)

```javascript
// Fetch General Ledger
fetch('/api/general-ledger/?company=4B-BIO&from_date=2024-01-01&to_date=2024-12-31&group_by_account=true')
  .then(response => response.json())
  .then(data => {
    console.log(data.data.accounts);  // Grouped by account
    console.log(data.data.grand_total);  // Total debit/credit
  });

// Fetch Chart of Accounts
fetch('/api/chart-of-accounts/?company=4B-BIO')
  .then(response => response.json())
  .then(data => {
    console.log(data.data);  // All accounts
  });
```

### Admin Interface

1. Navigate to: `http://localhost:8000/admin/general-ledger/`
2. Select company database
3. Apply filters:
   - Account range (From/To)
   - Date range (From/To)
   - Business Partner
   - Project
   - Transaction Type
4. View grouped ledger by account
5. Export to CSV

## API Query Parameters

### `/api/general-ledger/`
- `company` - Company key (4B-BIO, 4B-ORANG) - **Required**
- `account_from` - Start account code
- `account_to` - End account code
- `from_date` - Start date (YYYY-MM-DD)
- `to_date` - End date (YYYY-MM-DD)
- `bp_code` - Business Partner CardCode
- `project_code` - Project Code
- `trans_type` - Transaction Type (13, 30, etc.)
- `page` - Page number (default: 1)
- `page_size` - Records per page (default: 50)
- `group_by_account` - Group by account (true/false, default: false)

## Response Format

### Grouped by Account (group_by_account=true)
```json
{
  "success": true,
  "data": {
    "accounts": [
      {
        "Account": "11010100",
        "AccountName": "Cash in Hand",
        "OpeningBalance": 1000.00,
        "transactions": [
          {
            "PostingDate": "2024-01-15",
            "TransId": 12345,
            "Debit": 500.00,
            "Credit": 0.00,
            "RunningBalance": 1500.00,
            ...
          }
        ],
        "TotalDebit": 5000.00,
        "TotalCredit": 3000.00,
        "ClosingBalance": 3000.00
      }
    ],
    "grand_total": {
      "TotalDebit": 50000.00,
      "TotalCredit": 50000.00,
      "Difference": 0.00
    }
  },
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_records": 234,
    "total_pages": 5
  }
}
```

### Flat List (group_by_account=false)
```json
{
  "success": true,
  "data": {
    "transactions": [
      {
        "PostingDate": "2024-01-15",
        "TransId": 12345,
        "Account": "11010100",
        "AccountName": "Cash in Hand",
        "Debit": 500.00,
        "Credit": 0.00,
        "RunningBalance": 1500.00,
        ...
      }
    ],
    "grand_total": {
      "TotalDebit": 50000.00,
      "TotalCredit": 50000.00,
      "Balance": 0.00
    }
  },
  "pagination": {...}
}
```

## Database Tables Used

### HANA Tables
- `OJDT` - Journal Entry Header
- `JDT1` - Journal Entry Lines
- `OACT` - Chart of Accounts
- `OCRD` - Business Partners
- `OPRJ` - Projects

## Configuration

### Environment Variables (.env)
```env
HANA_HOST=fourbtest.vdc.services
HANA_PORT=30015
HANA_USER=FASTAPP
HANA_PASSWORD=@uF!56%3##
HANA_ENCRYPT=true
```

### Django Settings (preferences.Setting)
- `SAP_COMPANY_DB` - Company database mapping
  ```json
  {
    "4B-BIO": "4B-BIO_APP",
    "4B-ORANG": "4B-ORANG_APP"
  }
  ```

## Features

### Admin Interface Features
- ✅ Multi-company database switching
- ✅ Account range filtering
- ✅ Date range filtering
- ✅ Business Partner filtering
- ✅ Project filtering
- ✅ Transaction type filtering
- ✅ Grouped display by account
- ✅ Opening balance calculation
- ✅ Running balance per transaction
- ✅ Closing balance per account
- ✅ Grand total with debit/credit verification
- ✅ Pagination (accounts level)
- ✅ CSV export
- ✅ Responsive design

### API Features
- ✅ RESTful endpoints
- ✅ Swagger documentation
- ✅ Pagination support
- ✅ Flexible grouping (flat or by account)
- ✅ Opening/closing balance calculation
- ✅ Running balance calculation
- ✅ Grand total calculation
- ✅ Error handling

## File Structure

```
general_ledger/
├── __init__.py
├── admin.py
├── apps.py
├── models.py (empty - no database models needed)
├── tests.py
├── views.py (API and admin views)
├── urls.py (URL configuration)
├── hana_queries.py (HANA SQL queries)
├── utils.py (Helper functions)
├── templates/
│   └── general_ledger/
│       └── general_ledger.html (Admin UI template)
└── migrations/
```

## Dependencies

- `hdbcli` - SAP HANA database client
- `rest_framework` - Django REST Framework
- `drf_yasg` - Swagger documentation

## Swagger Documentation

Visit: `http://localhost:8000/swagger/`

Search for "General Ledger" tag to see all endpoints.

## Troubleshooting

### Connection Issues
- Verify HANA credentials in `.env`
- Check network connectivity to SAP server
- Verify schema name matches company database

### No Data Returned
- Ensure filters are correct (account range, date range)
- Check if data exists in HANA tables for selected company
- Verify user has permissions to query HANA

### Performance Issues
- Use narrower date ranges
- Filter by specific accounts
- Reduce page_size parameter
- Consider adding indexes on HANA tables

## Future Enhancements

- [ ] Redis caching for frequently accessed date ranges
- [ ] Excel export with formatting (currently CSV only)
- [ ] Transaction drill-down modal (view all lines of a journal entry)
- [ ] Account hierarchy display (parent-child)
- [ ] Filter by account type (Assets, Liabilities, etc.)
- [ ] Background report generation with Celery
- [ ] Email delivery of large reports
- [ ] Dashboard widgets for React app

## License

Internal use only - AgriGenie Project

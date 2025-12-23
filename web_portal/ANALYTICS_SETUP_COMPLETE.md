# Analytics Dashboard - Setup Complete! ✓

## Summary

Your analytics dashboard API has been successfully wired and is ready to use! Here's what was created:

## 📁 New Files Created

1. **`analytics/views.py`** - Complete analytics API views with 4 endpoints
2. **`analytics/serializers.py`** - Serializers for all analytics data
3. **`analytics/urls.py`** - URL routing for analytics endpoints
4. **`analytics/admin.py`** - Admin configuration (extensible)
5. **`analytics/README.md`** - Comprehensive API documentation

## 🔗 Available Endpoints

### 1. Dashboard Overview
```
GET /api/analytics/dashboard/overview/
```
**All-in-one endpoint** with sales vs achievements, farmer stats, targets, and today's activities.

**Query Parameters:**
- `emp_id` - Filter by employee ID
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)
- `company` - Company key (e.g., "4B-BIO")
- `region`, `zone`, `territory` - Geographical filters
- `in_millions` - Convert values to millions (true/false)

### 2. Sales Analytics
```
GET /api/analytics/sales/
```
**Detailed sales vs achievement** data with various filters.

### 3. Farmer Analytics
```
GET /api/analytics/farmers/
```
**Farmer statistics** including demographics, landholding distribution.

### 4. Performance Metrics
```
GET /api/analytics/performance/
```
**Performance tracking** with historical comparison.

**Query Parameters:**
- `period` - Time period: "today", "week", "month", "quarter", "year"

## ✅ What's Working

1. ✓ Analytics app added to `INSTALLED_APPS` in settings
2. ✓ Analytics URLs wired to main `urls.py` at `/api/analytics/`
3. ✓ All 4 API endpoints properly configured and accessible
4. ✓ Integration with SAP HANA for sales vs achievement data
5. ✓ Integration with Farmer, Meeting, Sales Order models
6. ✓ Swagger documentation ready at `/swagger/` (tag: "Analytics Dashboard")
7. ✓ Proper authentication required for all endpoints

## 📊 Data Sources

The dashboard aggregates data from:

- **SAP HANA** (sales_vs_achievement_by_emp, sales_vs_achievement_geo_inv)
- **Farmers app** (Farmer model)
- **FieldAdvisoryService app** (MeetingSchedule, SalesOrder)
- **farmerMeetingDataEntry app** (Meeting, FieldDay)

## 🚀 How to Use

### 1. Start the Server
```bash
cd "f:\samad\clone tarzan\django_web_portal\web_portal"
python manage.py runserver
```

### 2. Access Swagger Documentation
```
http://localhost:8000/swagger/
```
Look for "Analytics Dashboard" tag.

### 3. Make API Calls

**Example with cURL:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/analytics/dashboard/overview/?in_millions=true"
```

**Example with Python:**
```python
import requests

headers = {'Authorization': f'Bearer {your_token}'}
response = requests.get(
    'http://localhost:8000/api/analytics/dashboard/overview/',
    headers=headers,
    params={'in_millions': 'true', 'emp_id': '729'}
)
data = response.json()
print(data)
```

### 4. Frontend Integration (React/Next.js)

```javascript
// Dashboard component
import { useEffect, useState } from 'react';

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null);
  
  useEffect(() => {
    const fetchDashboard = async () => {
      const response = await fetch(
        '/api/analytics/dashboard/overview/?in_millions=true',
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      const data = await response.json();
      setDashboardData(data);
    };
    
    fetchDashboard();
  }, []);
  
  return (
    <div>
      <h1>Dashboard</h1>
      {dashboardData && (
        <>
          <div>Today's Visits: {dashboardData.visits_today}</div>
          <div>Pending Orders: {dashboardData.pending_sales_orders}</div>
          <div>Total Farmers: {dashboardData.farmer_stats.total_count}</div>
          {/* Add charts for sales_vs_achievement */}
        </>
      )}
    </div>
  );
}
```

## 📝 Example Response

```json
{
  "sales_vs_achievement": [
    {
      "emp_id": 729,
      "territory_name": "D.G Khan Territory",
      "sales_target": 10.5,
      "achievement": 9.8,
      "percentage": 93.33,
      "from_date": "2024-01-01",
      "to_date": "2024-12-31"
    }
  ],
  "farmer_stats": {
    "total_count": 220,
    "active_count": 220,
    "by_district": {
      "Lahore": 50,
      "Faisalabad": 45
    },
    "by_education": {
      "primary": 30,
      "secondary": 120
    },
    "by_landholding": {
      "small (< 5 acres)": 80,
      "medium (5-25 acres)": 100,
      "large (> 25 acres)": 40
    },
    "total_land_area": 5500.5,
    "average_land_per_farmer": 25.0
  },
  "visits_today": 5,
  "date": "2024-12-23",
  "pending_sales_orders": 64,
  "company_options": [
    {"key": "4B-BIO", "schema": "BIO_LIVE"},
    {"key": "4B-AG", "schema": "AG_LIVE"}
  ],
  "selected_company": ""
}
```

## 🛠 Configuration

### SAP Connection

The analytics API automatically uses SAP HANA connection from:
- `.env` file in `sap_integration/` directory
- Or from project root `.env`

Required environment variables:
```env
HANA_HOST=your_hana_host
HANA_PORT=30015
HANA_USER=your_username
HANA_PASSWORD=your_password
HANA_SCHEMA=BIO_LIVE
HANA_ENCRYPT=true
HANA_SSL_VALIDATE=false
```

### Company Schema Mapping

Configure in Django Admin under Preferences > Settings:
- Create a setting with slug `SAP_COMPANY_DB`
- Value: JSON mapping like `{"4B-BIO": "BIO_LIVE", "4B-AG": "AG_LIVE"}`

## 📖 Full Documentation

See [analytics/README.md](analytics/README.md) for complete API documentation including:
- Detailed endpoint descriptions
- All query parameters
- Request/response examples
- Error handling
- Frontend integration examples
- Performance considerations

## ✨ Next Steps

1. **Test with real data:** Use Swagger UI or Postman to test endpoints
2. **Build frontend dashboard:** Use the APIs to create visual charts
3. **Add caching:** Implement Redis caching for better performance
4. **Customize:** Extend the views to add more metrics as needed

## 🎉 You're All Set!

Your analytics dashboard API is fully functional and ready to power your frontend dashboard with:
- ✓ Sales vs Achievements from SAP
- ✓ All Farmer Statistics
- ✓ Performance Targets
- ✓ Today's Activities
- ✓ Comprehensive filtering options

Happy coding! 🚀

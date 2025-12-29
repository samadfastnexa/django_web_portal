# Analytics App

## Overview

The Analytics app provides comprehensive dashboard and reporting APIs that aggregate data from multiple sources including:
- Sales vs Achievement (SAP Integration)
- Farmer Statistics
- Performance Metrics
- Activity Tracking

## API Endpoints

### 1. Dashboard Overview
**Endpoint:** `GET /api/analytics/dashboard/overview/`

**Description:** Main dashboard endpoint that aggregates all key metrics in one response

**Query Parameters:**
- `emp_id` (optional): Employee ID for SAP data filtering
- `start_date` (optional): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format
- `company` (optional): Company key (e.g., "4B-BIO")
- `region` (optional): Region filter for geographical data
- `zone` (optional): Zone filter for geographical data
- `territory` (optional): Territory filter for geographical data
- `in_millions` (optional): Convert monetary values to millions (true/false)

**Example Request:**
```bash
GET /api/analytics/dashboard/overview/?emp_id=729&start_date=2024-01-01&end_date=2024-12-31&in_millions=true
```

**Response:**
```json
{
  "sales_vs_achievement": [
    {
      "emp_id": 729,
      "territory_id": 1,
      "territory_name": "D.G Khan Territory",
      "sales_target": 10.5,
      "achievement": 9.8,
      "from_date": "2024-01-01",
      "to_date": "2024-12-31",
      "percentage": 93.33
    }
  ],
  "farmer_stats": {
    "total_count": 220,
    "active_count": 215,
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
  "pending_sales_orders": 64,
  "company_options": [
    {"key": "4B-BIO", "schema": "BIO_LIVE"},
    {"key": "4B-AG", "schema": "AG_LIVE"}
  ],
  "selected_company": "4B-BIO"
}
```

---

### 2. Sales Analytics
**Endpoint:** `GET /api/analytics/sales/`

**Description:** Detailed sales vs achievement analytics with various filters

**Query Parameters:**
- `emp_id` (optional): Employee ID
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `region` (optional): Region filter
- `zone` (optional): Zone filter
- `territory` (optional): Territory filter
- `company` (optional): Company key
- `group_by_emp` (optional): Group results by employee (true/false)
- `in_millions` (optional): Convert to millions (true/false)

**Example Request:**
```bash
GET /api/analytics/sales/?region=Punjab&start_date=2024-01-01&in_millions=true
```

**Response:**
```json
{
  "sales_vs_achievement": [
    {
      "emp_id": 729,
      "territory_name": "Lahore Territory",
      "sales_target": 15.2,
      "achievement": 14.5,
      "percentage": 95.39
    }
  ],
  "company_options": [...],
  "selected_company": ""
}
```

---

### 3. Farmer Analytics
**Endpoint:** `GET /api/analytics/farmers/`

**Description:** Detailed farmer statistics and demographics

**Query Parameters:**
- `district` (optional): Filter by district
- `education_level` (optional): Filter by education level
- `min_land_area` (optional): Minimum land area filter
- `max_land_area` (optional): Maximum land area filter

**Example Request:**
```bash
GET /api/analytics/farmers/?district=Lahore&education_level=secondary
```

**Response:**
```json
{
  "total_count": 150,
  "active_count": 145,
  "by_district": {
    "Lahore": 150
  },
  "by_education": {
    "secondary": 150
  },
  "by_landholding": {
    "small (< 5 acres)": 50,
    "medium (5-25 acres)": 70,
    "large (> 25 acres)": 30
  },
  "total_land_area": 3750.0,
  "average_land_per_farmer": 25.0
}
```

---

### 4. Performance Metrics
**Endpoint:** `GET /api/analytics/performance/`

**Description:** Track key performance indicators over time with historical comparison

**Query Parameters:**
- `period` (optional): Time period - "today", "week", "month" (default), "quarter", "year"

**Example Request:**
```bash
GET /api/analytics/performance/?period=month
```

**Response:**
```json
[
  {
    "metric_name": "Total Visits",
    "current_value": 45,
    "previous_value": 38,
    "unit": "visits",
    "trend": "up"
  },
  {
    "metric_name": "Sales Orders Created",
    "current_value": 120,
    "previous_value": 110,
    "unit": "orders",
    "trend": "up"
  },
  {
    "metric_name": "Farmers Registered",
    "current_value": 25,
    "previous_value": 20,
    "unit": "farmers",
    "trend": "up"
  }
]
```

---

## Authentication

All analytics endpoints require authentication. Include your JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

---

## Data Sources

The analytics app aggregates data from:

1. **SAP HANA** (via sap_integration app)
   - Sales vs Achievement
   - Territory data
   - Target information

2. **Local Database**
   - Farmers (farmers app)
   - Meetings & Field Days (farmerMeetingDataEntry app)
   - Sales Orders (FieldAdvisoryService app)
   - Meeting Schedules (FieldAdvisoryService app)

---

## Integration with Frontend Dashboard

### Recommended Dashboard Layout

1. **Top Cards/KPIs:**
   - Today's Visits
   - Pending Sales Orders
   - Total Farmers
   - Sales vs Achievement Summary

2. **Sales Chart:**
   - Bar/Line chart showing targets vs achievements
   - Filter by territory, region, zone
   - Date range selector

3. **Farmer Distribution:**
   - Pie charts for district distribution
   - Education level breakdown
   - Landholding size categories

4. **Performance Trends:**
   - Line chart showing metrics over time
   - Period selector (day/week/month/quarter/year)

### Example Frontend Implementation (React)

```javascript
// Fetch dashboard overview
const fetchDashboard = async () => {
  const response = await fetch(
    '/api/analytics/dashboard/overview/?in_millions=true',
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  const data = await response.json();
  return data;
};

// Fetch with filters
const fetchSalesData = async (filters) => {
  const params = new URLSearchParams(filters);
  const response = await fetch(
    `/api/analytics/sales/?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  return await response.json();
};
```

---

## Error Handling

All endpoints return standard HTTP status codes:
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `500 Internal Server Error`: Server error

Error responses include a descriptive message:
```json
{
  "error": "SAP integration not available"
}
```

---

## Performance Considerations

1. **Caching:** Consider implementing caching for dashboard data that doesn't change frequently
2. **Date Ranges:** Limit date ranges for large datasets to improve performance
3. **Pagination:** For detailed lists, use pagination (to be implemented)
4. **Aggregation:** Data is aggregated on the backend to minimize payload size

---

## Future Enhancements

- [ ] Add caching layer (Redis)
- [ ] Implement real-time updates (WebSocket)
- [ ] Export functionality (Excel, PDF)
- [ ] Scheduled reports
- [ ] Custom dashboard widgets
- [ ] Advanced filtering and drill-down
- [ ] Comparative analytics (year-over-year)
- [ ] Predictive analytics (ML-based forecasting)

---

## Testing

Test the endpoints using:

1. **Swagger UI:** Navigate to `/swagger/` and look for "Analytics Dashboard" tag

2. **cURL:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/analytics/dashboard/overview/"
```

3. **Python requests:**
```python
import requests

headers = {'Authorization': f'Bearer {token}'}
response = requests.get(
    'http://localhost:8000/api/analytics/dashboard/overview/',
    headers=headers,
    params={'in_millions': 'true'}
)
print(response.json())
```

---

## Support

For issues or questions, contact the development team or refer to:
- Main project README
- API documentation in Swagger
- SAP Integration documentation

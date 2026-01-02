# Policy Linking APIs - Quick Reference

## 🔗 New Endpoints Summary

### Endpoint 1: Policy Items
```
GET /api/sap/policy-items/
```
**Get items in a policy** with optional customer filter

| Parameter | Required | Type | Example |
|-----------|----------|------|---------|
| doc_entry | ✓ | string | "18" |
| card_code | | string | "C-00001" |
| database | | string | "4B-BIO-app" |
| page | | integer | 1 |
| page_size | | integer | 50 |

**Response:** Items with ItemCode, ItemName, unit_price, Currency

---

### Endpoint 2: Policy Project Link
```
GET /api/sap/policy-project-link/
```
**Get projects linked to policies** for a specific customer

| Parameter | Required | Type | Example |
|-----------|----------|------|---------|
| card_code | ✓ | string | "BIC00611" |
| database | | string | "4B-ORANG-app" |
| page | | integer | 1 |
| page_size | | integer | 50 |

**Response:** Projects with project_code, project_name, validity info

---

## 📋 Common Use Cases

### 1️⃣ Show Customer All Items in Their Policy
```bash
GET /api/sap/policy-items/?doc_entry=18&card_code=C-00001
```

### 2️⃣ Show Customer Their Project Assignments
```bash
GET /api/sap/policy-project-link/?card_code=C-00001
```

### 3️⃣ Cross-Database Query (ORANG)
```bash
GET /api/sap/policy-project-link/?card_code=C-00001&database=4B-ORANG-app
```

### 4️⃣ Paginated Results (20 per page)
```bash
GET /api/sap/policy-items/?doc_entry=18&page=1&page_size=20
```

---

## 🔄 Response Structure

### Success (200)
```json
{
  "success": true,
  "page": 1,
  "num_pages": 3,
  "count": 125,
  "data": [...]
}
```

### Error (400/500)
```json
{
  "success": false,
  "error": "description of error"
}
```

---

## 📊 Database Tables

### Policy Items
```
@PL1 (Policy Header)
  └─ @PLR4 (Policy Items)
```

### Policy Projects
```
@PLR8 (Policy Assignments)
  ├─ @PL1 (Policy Header)
  └─ OPRJ (Projects Master)
```

---

## ✅ Key Features

- ✅ Multi-database support (BIO & ORANG)
- ✅ Pagination (default: 50 items/page)
- ✅ Full Swagger docs
- ✅ Token authentication required
- ✅ Date formatting (ISO format)
- ✅ Error handling & validation

---

## 🧪 Testing

```bash
# Test Policy Items
python test_policy_items_api.py

# Test Policy Projects
python test_policy_project_link_api.py
```

---

## 📖 Full Documentation

- `POLICY_ITEMS_API_GUIDE.md` - Detailed Policy Items docs
- `POLICY_PROJECT_LINK_API_GUIDE.md` - Detailed Policy Projects docs
- `POLICY_LINKING_ENDPOINTS.md` - Integration guide

---

## 🔐 Authentication

All endpoints require:
```
Authorization: Token {your-auth-token}
```

---

## 📱 Integration Examples

### cURL
```bash
curl "http://localhost:8000/api/sap/policy-items/?doc_entry=18" \
  -H "Authorization: Token YOUR_TOKEN"
```

### Python
```python
import requests
response = requests.get(
  "http://localhost:8000/api/sap/policy-items/?doc_entry=18",
  headers={"Authorization": "Token YOUR_TOKEN"}
)
data = response.json()
```

### JavaScript
```javascript
fetch("http://localhost:8000/api/sap/policy-items/?doc_entry=18", {
  headers: {"Authorization": "Token YOUR_TOKEN"}
})
.then(r => r.json())
.then(data => console.log(data))
```

---

## ⚡ Quick Tips

1. **Default Database:** 4B-BIO-app (use `?database=4B-ORANG-app` for ORANG)
2. **Required Params:** doc_entry for items, card_code for projects
3. **Pagination:** Default 50/page, max 200/page
4. **Dates:** All returned in YYYY-MM-DD format
5. **Error Codes:** 400=validation, 500=server error

---

## 🗓️ Changelog

**2026-01-02** - Initial Release
- Policy Items endpoint
- Policy Project Link endpoint
- Full documentation
- Test scripts

---

## 📞 Support

For issues or questions:
1. Check Swagger docs at `/swagger/`
2. Review full guides in .md files
3. Run test scripts to verify setup
4. Check .env configuration

---

Generated: 2026-01-02
Version: 1.0

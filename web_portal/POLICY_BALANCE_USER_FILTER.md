# Policy Customer Balance - User Filter Feature

## Overview
Enhanced both policy customer balance endpoints to support user-based filtering and validation:
1. **List endpoint** (`/api/sap/policy-customer-balance/`) - Filter all balances by user
2. **Detail endpoint** (`/api/sap/policy-customer-balance/{card_code}/`) - Optionally validate card_code belongs to user

## Endpoints

### 1. List All Policy Customer Balances

**URL:** `/api/sap/policy-customer-balance/`  
**Method:** `GET`  
**Tags:** SAP

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database` | string | No | Database/schema (4B-BIO_APP or 4B-ORANG_APP). If not provided, uses default from settings. |
| `user` | string | No | **Filter by user ID or username.** Returns customer card codes and policy balances for all dealers assigned to this user. |
| `limit` | integer | No | Maximum number of records to return (default: 200). Only applies when not filtering by user. |

#### Usage Examples

**Get all policy balances:**
```
GET /api/sap/policy-customer-balance/?database=4B-BIO
```

**Get balances for user ID 5:**
```
GET /api/sap/policy-customer-balance/?database=4B-BIO&user=5
```

**Get balances for user by username:**
```
GET /api/sap/policy-customer-balance/?database=4B-BIO&user=john_dealer
```

---

### 2. Get Policy Customer Balance by CardCode

**URL:** `/api/sap/policy-customer-balance/{card_code}/`  
**Method:** `GET`  
**Tags:** SAP

#### Parameters

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `card_code` | string | Yes | SAP customer card code (e.g., ORC00002) |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database` | string | No | Database/schema (4B-BIO_APP or 4B-ORANG_APP). If not provided, uses default from settings. |
| `user` | string | No | **NEW:** Optional user ID or username. If provided, verifies that the card_code belongs to this user. Returns 403 Forbidden if card_code does not belong to user. |

#### Usage Examples

**Get specific customer balance (existing):**
```
GET /api/sap/policy-customer-balance/ORC00002/?database=4B-ORANG
```

**Get customer balance with user validation (NEW):**
```
GET /api/sap/policy-customer-balance/ORC00002/?database=4B-ORANG&user=5
```

**Get customer balance with user validation by username (NEW):**
```
GET /api/sap/policy-customer-balance/ORC00002/?database=4B-ORANG&user=john_dealer
```

---

## Response Format

### Success Response (200 OK)
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "CardCode": "string",
      "CardName": "string",
      "ProjectCode": "string",
      "PolicyNumber": "string",
      "Balance": float,
      "Currency": "string"
    }
  ]
}
```

### Error Responses

#### User Not Found (404 Not Found)
```json
{
  "success": false,
  "error": "User \"nonexistent_user\" not found"
}
```

#### Card Code Does Not Belong to User (403 Forbidden)
```json
{
  "success": false,
  "error": "Card code \"ORC00002\" does not belong to user \"john_dealer\""
}
```

#### Server Error (500 Internal Server Error)
```json
{
  "success": false,
  "error": "Error message details"
}
```

---

## Implementation Details

### List Endpoint (`policy_customer_balance_list()`)

When `user` parameter is provided:
1. Parses user as integer (ID) or string (username)
2. Queries `User` model to find matching user
3. Retrieves all dealers linked to the user via `Dealer.user` foreign key
4. Extracts `card_code` from each dealer (excluding null/empty)
5. Fetches policy balance for each card code
6. Aggregates and returns combined results

### Detail Endpoint (`policy_customer_balance_detail()`)

When `user` parameter is provided:
1. Parses user as integer (ID) or string (username)
2. Queries `User` model to find matching user
3. Verifies the requested `card_code` belongs to a dealer assigned to that user
4. Returns 403 Forbidden if card_code doesn't belong to user
5. Otherwise proceeds with fetching the balance for the card_code

When `user` parameter is NOT provided:
- Works exactly as before (fetches balance for the provided card_code)

### Database Relationships

```
User (accounts.User)
  └─ has OneToOne Dealer (FieldAdvisoryService.Dealer)
       ├─ has card_code → maps to SAP customer in HANA
       └─ belongs to Company, Region, Zone, Territory

Dealer.card_code (string)
  └─ references SAP business partner in B4_PAYMENT_TARGET
       └─ has policy balances in SAP
```

---

## Swagger Documentation

### List Endpoint
- `database` parameter with enum values: 4B-BIO-app, 4B-ORANG-app
- `user` parameter to filter by user ID or username
- `limit` parameter for pagination
- Response code: 200 (OK), 404 (User not found), 500 (Server Error)

### Detail Endpoint
- `card_code` path parameter (required)
- `database` query parameter
- **NEW:** `user` query parameter with validation
- Response codes: 200 (OK), 403 (Forbidden), 404 (User not found), 500 (Server Error)

---

## Testing

### Test Script

Run the comprehensive test script:
```bash
python test_policy_user_balance.py
```

### Manual Testing via cURL

**List endpoint - all balances:**
```bash
curl "http://localhost:8000/api/sap/policy-customer-balance/?database=4B-BIO"
```

**List endpoint - user 1's balances:**
```bash
curl "http://localhost:8000/api/sap/policy-customer-balance/?database=4B-BIO&user=1"
```

**Detail endpoint - specific card code:**
```bash
curl "http://localhost:8000/api/sap/policy-customer-balance/ORC00002/?database=4B-ORANG"
```

**Detail endpoint - with user validation:**
```bash
curl "http://localhost:8000/api/sap/policy-customer-balance/ORC00002/?database=4B-ORANG&user=1"
```

**Detail endpoint - invalid user:**
```bash
curl "http://localhost:8000/api/sap/policy-customer-balance/ORC00002/?database=4B-ORANG&user=invalid"
```
Expected response: 404 User not found

**Detail endpoint - card code doesn't belong to user:**
```bash
curl "http://localhost:8000/api/sap/policy-customer-balance/ORC00999/?database=4B-ORANG&user=1"
```
Expected response: 403 Card code does not belong to user

---

## Use Cases

### Use Case 1: Mobile App - Show User's Customers
A mobile app wants to display only the customers (dealers) assigned to the logged-in user. It calls:
```
GET /api/sap/policy-customer-balance/?user={current_user_id}
```
This returns policy balances for all dealers assigned to the user.

### Use Case 2: API Security - Validate Permission
Before showing a specific customer's balance, an app wants to ensure the requested card_code belongs to the requesting user:
```
GET /api/sap/policy-customer-balance/{card_code}/?user={current_user_id}
```
If the user doesn't own that card_code, the API returns 403 Forbidden.

### Use Case 3: Admin Dashboard - All Customers
An admin dashboard wants all customers without user filtering:
```
GET /api/sap/policy-customer-balance/?database=4B-BIO&limit=500
```
Returns all customer balances.

---

## Backward Compatibility

✅ **Fully backward compatible:**
- Existing calls without `user` parameter work exactly as before
- List endpoint without `user` returns all customers
- Detail endpoint without `user` returns balance for any card code
- All existing parameters continue to work
- No breaking changes to response format
- New parameters are optional

---

## Code Changes

### Modified Files

**`sap_integration/views.py`**

1. **`get_policy_customer_balance_data()` function**
   - Added user parameter handling for list endpoint
   - Queries User and Dealer models
   - Aggregates balances from multiple dealers

2. **`policy_customer_balance_detail()` function**
   - Added user parameter validation logic
   - Verifies card_code belongs to user
   - Returns 403 Forbidden if validation fails

3. **Swagger decorators**
   - Added user parameter to both endpoints
   - Added 403 and 404 response codes for detail endpoint
   - Enhanced operation descriptions

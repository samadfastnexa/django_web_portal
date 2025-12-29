# Sales Order API - Mobile Developer Guide

## Overview
The Sales Order POST API has been updated to make **all fields optional**, matching the admin panel's flexible behavior and making it easier for mobile developers to use.

## Key Changes
✅ **No mandatory fields** - Send only what you need  
✅ **Flexible field handling** - All SAP fields are optional  
✅ **Simplified validation** - Reduced validation errors  
✅ **Better mobile UX** - Build orders step-by-step  

## API Endpoints

### Create Sales Order (POST)
```
POST /api/sales-orders/
```

### Update Sales Order (PATCH)
```
PATCH /api/sales-orders/{id}/
```

## Minimal Request Example
You can create a sales order with just the fields you have:

```json
{
    "staff": 1,
    "comments": "Order from mobile app"
}
```

## Common Mobile App Request
Typical fields mobile apps would send:

```json
{
    "staff": 1,
    "dealer": 5,
    "card_code": "C20000",
    "card_name": "ABC Traders",
    "comments": "Mobile order - needs review",
    "status": "pending"
}
```

## Full Example with SAP Fields
When you have all customer/SAP data:

```json
{
    "staff": 1,
    "dealer": 5,
    "schedule": 10,
    "status": "pending",
    
    "series": 8,
    "doc_type": "dDocument_Items",
    "doc_date": "2024-01-15",
    "doc_due_date": "2024-02-15",
    "tax_date": "2024-01-15",
    
    "card_code": "C20000",
    "card_name": "ABC Traders",
    "contact_person_code": 1,
    "federal_tax_id": "1234567-8",
    "address": "123 Main Street, Lahore",
    
    "doc_currency": "PKR",
    "doc_rate": 1.0,
    
    "comments": "Rush order - customer requested early delivery",
    "summery_type": "dNoSummary",
    
    "u_sotyp": "SO",
    "u_usid": "mobile_user_123",
    "u_s_card_code": "C20001",
    "u_s_card_name": "Child Customer"
}
```

## Updating Existing Orders
Use PATCH to update only specific fields:

### Update Status Only
```json
{
    "status": "entertained"
}
```

### Add Comments
```json
{
    "comments": "Customer confirmed delivery address"
}
```

### Update SAP Response After Posting
```json
{
    "is_posted_to_sap": true,
    "sap_doc_entry": 12345,
    "sap_doc_num": 100234,
    "posted_at": "2024-01-15T14:30:00Z"
}
```

## Field Reference

### Basic Fields
| Field | Type | Description |
|-------|------|-------------|
| `staff` | integer | User ID creating the order |
| `dealer` | integer | Dealer ID (optional) |
| `schedule` | integer | Meeting schedule ID (optional) |
| `status` | string | Order status: `pending`, `entertained`, `rejected`, `closed` |
| `comments` | string | Order remarks/notes |

### Customer Information
| Field | Type | Description |
|-------|------|-------------|
| `card_code` | string | Customer BP Code from SAP |
| `card_name` | string | Customer name |
| `contact_person_code` | integer | Contact person code |
| `federal_tax_id` | string | Customer NTN/Tax ID |
| `address` | text | Billing address |

### SAP Document Fields
| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `series` | integer | Document series | 8 |
| `doc_type` | string | Document type | `dDocument_Items` |
| `doc_date` | date | Document date | - |
| `doc_due_date` | date | Due date | - |
| `tax_date` | date | Tax date | - |
| `doc_currency` | string | Currency code | `PKR` |
| `doc_rate` | decimal | Exchange rate | 1.0 |
| `summery_type` | string | Summary type | `dNoSummary` |
| `doc_object_code` | string | Object code | `oOrders` |

### User Defined Fields (UDF)
| Field | Type | Description |
|-------|------|-------------|
| `u_sotyp` | string | Sales Order Type |
| `u_usid` | string | Portal User ID |
| `u_swje` | string | SWJE |
| `u_secje` | string | SECJE |
| `u_crje` | string | CRJE |
| `u_s_card_code` | string | Child Customer Code |
| `u_s_card_name` | string | Child Customer Name |

### SAP Response Fields (Read-Only)
| Field | Type | Description |
|-------|------|-------------|
| `sap_doc_entry` | integer | SAP Document Entry (after posting) |
| `sap_doc_num` | integer | SAP Document Number (after posting) |
| `sap_error` | text | SAP error message if posting failed |
| `sap_response_json` | text | Complete SAP API response |
| `is_posted_to_sap` | boolean | Posted to SAP successfully |
| `posted_at` | datetime | When posted to SAP |

## Response Format
Successful creation returns 201 with full order data:

```json
{
    "id": 123,
    "staff": 1,
    "dealer": 5,
    "card_code": "C20000",
    "card_name": "ABC Traders",
    "status": "pending",
    "created_at": "2024-01-15T10:30:00Z",
    "is_posted_to_sap": false,
    ...
}
```

## Error Handling
```json
{
    "field_name": [
        "Error message description"
    ]
}
```

## Best Practices for Mobile Apps

1. **Start Simple**: Create orders with minimal fields, let users add details later
2. **Progressive Enhancement**: Use PATCH to update orders as users provide more information
3. **Status Tracking**: Use status field to track order lifecycle
4. **Error Recovery**: Handle validation errors gracefully, fields are flexible
5. **Offline Support**: Queue orders locally, sync when online (all fields optional makes this easier)

## Testing with Swagger
Visit your Swagger UI at `/swagger/` to test the API interactively. All fields will now show as optional (not required).

## Example Mobile Flow

### 1. Quick Order Creation (Offline)
```json
POST /api/sales-orders/
{
    "staff": 1,
    "comments": "Quick order from field"
}
```

### 2. Add Customer Later (Online)
```json
PATCH /api/sales-orders/123/
{
    "card_code": "C20000",
    "card_name": "ABC Traders"
}
```

### 3. Submit for Processing
```json
PATCH /api/sales-orders/123/
{
    "status": "entertained",
    "doc_date": "2024-01-15",
    "doc_due_date": "2024-02-15"
}
```

## Notes
- The admin panel uses the same flexible field structure
- Default values are applied automatically for some fields (series=8, doc_currency=PKR, etc.)
- SAP posting happens separately through admin panel or automated processes
- All timestamps (created_at, posted_at) are auto-generated

## Support
For questions or issues, refer to the admin panel's Sales Order form which uses the same field structure.

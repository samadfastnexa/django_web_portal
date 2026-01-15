# Dealer Login Quick Test Guide

## Test Scenario: Create Dealer with User Account & Login

### Step 1: Create Dealer via Admin
1. Go to: `http://localhost:8000/admin/`
2. Navigate: **Field Advisory Service** → **Dealers** → **Add Dealer**
3. Fill form:
   ```
   Dealer Information:
   - Name: Test Dealer Corp
   - CNIC Number: 12345-6789012-3
   - Contact Number: 03001234567
   - Address: 123 Main Street, Karachi
   - Company: (Select any)
   - Region: (Select any)
   - Zone: (Select any)
   - Territory: (Select any)
   
   User Account (Optional):
   - Username: test_dealer
   - Email: testdealer@example.com
   - Password: TestPass123
   - First Name: Test
   - Last Name: Dealer
   ```
4. Upload CNIC images (front and back)
5. Click **SAVE**

### Step 2: Verify Dealer Created
- Admin → Dealers → Check new dealer in list
- Should show: Username, Email, Phone, Company, Active status

### Step 3: Test Dealer Login via API
Use Swagger or Postman:

**Request:**
```
POST http://localhost:8000/api/token/
Content-Type: application/json

{
  "username": "test_dealer",
  "password": "TestPass123"
}
```

**Expected Response (200 OK):**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTczNDU4Mjk2MCwiaWF0IjoxNzM0NDk2NTYwLCJqdGkiOiI1ZTJjMzFmZDhlMmI0YjZlYTdkMzc3ODk1NDAyMDEzZiIsInVzZXJfaWQiOjE2fQ.9_8J7k-VqJLp8FwZrm3X2K0Q4i8K5l6M9nO7PqRsT6U",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM0NDk2ODYwLCJpYXQiOjE3MzQ0OTY1NjAsImp0aSI6IjI1NzhhMzA1YTBjYjQyNzliMWM2OGJhOGM2ZWE5ZTgyIiwidXNlcl9pZCI6MTZ9.kJ0l9mN5o_i-PqRsTuVwXyZ1aB2cDeFgHiJ3kL4mNoPqRs"
}
```

### Step 4: Access Dealer Profile with Token
Copy the `access` token from step 3.

**Request:**
```
GET http://localhost:8000/api/dealers/5/
Authorization: Bearer <access_token>
```

**Expected Response (200 OK):**
```json
{
  "id": 5,
  "user": 16,
  "username": "test_dealer",
  "email": "testdealer@example.com",
  "first_name": "Test",
  "last_name": "Dealer",
  "name": "Test Dealer Corp",
  "cnic_number": "12345-6789012-3",
  "contact_number": "03001234567",
  "company": 1,
  "region": 1,
  "zone": 1,
  "territory": 1,
  "address": "123 Main Street, Karachi",
  "latitude": null,
  "longitude": null,
  "remarks": null,
  "is_active": true,
  "card_code": "D00005",
  "created_at": "2026-01-12T10:30:00Z",
  "updated_at": "2026-01-12T10:30:00Z"
}
```

### Step 5: Test API Create Dealer with New User
**Request:**
```
POST http://localhost:8000/api/dealers/
Content-Type: multipart/form-data

Form Data:
- name: API Created Dealer
- contact_number: 03009876543
- cnic_number: 98765-4321098-7
- company: 1
- region: 1
- zone: 1
- territory: 1
- address: 456 Second Avenue, Lahore
- username: api_dealer
- email: apidealer@example.com
- password: ApiPass456
- first_name: API
- last_name: Created
- cnic_front_image: <select file>
- cnic_back_image: <select file>
```

**Expected Response (201 Created):**
```json
{
  "id": 6,
  "user": 17,
  "username": "api_dealer",
  "email": "apidealer@example.com",
  "first_name": "API",
  "last_name": "Created",
  "name": "API Created Dealer",
  "cnic_number": "98765-4321098-7",
  "contact_number": "03009876543",
  "company": 1,
  "region": 1,
  "zone": 1,
  "territory": 1,
  "address": "456 Second Avenue, Lahore",
  "is_active": true,
  "card_code": "D00006",
  "created_at": "2026-01-12T11:00:00Z",
  "updated_at": "2026-01-12T11:00:00Z"
}
```

### Step 6: Verify in Admin
- Admin → Users → Should see new users (test_dealer, api_dealer)
- Admin → Dealers → Should see both dealers with user links

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 400 Error on dealer create | Check all required fields (name, CNIC, phone, company, CNIC images) |
| "User already exists" | Username/email already in use - pick different one |
| 401 Unauthorized | Token expired or invalid - re-login to get new token |
| "Dealer with this user already exists" | User is already linked to another dealer |
| No email field when creating | Email is optional but recommended for password reset |

## API Endpoints Available

```
# Authentication
POST   /api/token/                    - Login (get JWT tokens)
POST   /api/token/refresh/            - Refresh access token

# Dealer CRUD
GET    /api/dealers/                  - List all dealers
POST   /api/dealers/                  - Create new dealer
GET    /api/dealers/{id}/             - Get dealer details
PATCH  /api/dealers/{id}/             - Update dealer
DELETE /api/dealers/{id}/             - Delete dealer

# User (current logged-in user)
GET    /api/users/me/                 - Get current user profile
PATCH  /api/users/me/                 - Update current user profile
```

## Key Features Implemented

✅ Dealers linked to User accounts  
✅ Auto-create user account when creating dealer  
✅ Update user info (email, password, name) via dealer API  
✅ Login with username/password  
✅ JWT token-based authentication  
✅ Admin interface with user link  
✅ CNIC image storage  
✅ Geographic assignment (company, region, zone, territory)  
✅ Card code auto-generation  

## Next: Custom Permissions

To restrict dealers to only view their own profile:

```python
# In FieldAdvisoryService/views.py

from rest_framework.permissions import BasePermission

class IsDealerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Dealer can only access their own dealer record
        if request.user and hasattr(request.user, 'dealer'):
            return obj == request.user.dealer
        return False

# Update DealerViewSet:
class DealerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsDealerOrReadOnly]
    # ... rest of code
```

This would ensure dealers can only view/edit their own profile.

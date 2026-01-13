# Dealer Login & User Account Setup

## Overview
Dealers now have full user account integration, allowing them to login and manage their profiles. Each dealer is linked to a Django User account through a OneToOneField relationship.

## How It Works

### Database Relationship
```
User (Django Auth User)
├── username (unique)
├── email (unique)
├── password (hashed)
├── first_name
├── last_name
└── dealer (OneToOne) ←→ Dealer Model
    ├── name
    ├── cnic_number
    ├── contact_number
    ├── company, region, zone, territory
    └── is_active
```

## Creating a Dealer with User Account

### Method 1: Via API (Recommended for Automation)

#### Create Dealer with New User
```bash
POST /api/dealers/
Content-Type: multipart/form-data

Form Data:
- name: "ABC Traders"
- contact_number: "03001234567"
- cnic_number: "12345-6789012-3"
- company: 1
- region: 1
- zone: 1
- territory: 1
- address: "123 Main St, Karachi"
- username: "abc_trader"
- email: "dealer@abctraders.com"
- password: "SecurePass123"
- first_name: "Ahmed"
- last_name: "Khan"
- cnic_front_image: <file>
- cnic_back_image: <file>
```

**Response (201 Created):**
```json
{
  "id": 5,
  "user": 15,
  "username": "abc_trader",
  "email": "dealer@abctraders.com",
  "first_name": "Ahmed",
  "last_name": "Khan",
  "name": "ABC Traders",
  "cnic_number": "12345-6789012-3",
  "contact_number": "03001234567",
  "company": 1,
  "region": 1,
  "zone": 1,
  "territory": 1,
  "address": "123 Main St, Karachi",
  "is_active": true,
  "card_code": "D00005",
  "created_at": "2026-01-12T10:30:00Z",
  "updated_at": "2026-01-12T10:30:00Z"
}
```

#### Create Dealer with Existing User
```bash
POST /api/dealers/
Content-Type: multipart/form-data

Form Data:
- name: "XYZ Store"
- contact_number: "03009876543"
- cnic_number: "98765-4321098-7"
- company: 1
- region: 2
- user: 20  # Existing user ID
- address: "456 Second Ave, Lahore"
- cnic_front_image: <file>
- cnic_back_image: <file>
```

### Method 2: Via Django Admin

1. **Navigate to:** Admin Dashboard → Field Advisory Service → Dealers
2. **Click "Add Dealer"**
3. **Fill in form:**
   - **User Account section:**
     - User: (Leave empty to auto-create, or select existing user)
     - Card Code: (Auto-generated)
   - **Dealer Information:**
     - Name, CNIC, Phone, Address
   - **Geographic Assignment:**
     - Company, Region, Zone, Territory
   - **CNIC Images:** Upload front and back photos
4. **Fill user details (optional):**
   - Username (will auto-generate if not provided)
   - Email (required for login)
   - Password (will be hashed automatically)
   - First Name, Last Name

5. **Click "SAVE"**

## Dealer Login

### Login Endpoint
```bash
POST /api/token/
Content-Type: application/json

{
  "username": "abc_trader",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Using Token
```bash
GET /api/dealers/5/
Authorization: Bearer <access_token>
```

## Updating Dealer Account

### Update Dealer via API
```bash
PATCH /api/dealers/5/
Content-Type: multipart/form-data

Form Data:
- name: "ABC Traders Updated"
- email: "newemail@abctraders.com"
- password: "NewSecurePass456"
- contact_number: "03001111111"
```

### Update Dealer via Admin
1. Navigate to Dealers list
2. Click on dealer name
3. Modify fields:
   - User Account → Select different user
   - Email, Password, Name → Updates user account
   - Contact, CNIC, Address → Updates dealer info
4. Click "SAVE"

## Security Features

### Password Handling
- Passwords are **never returned** in API responses
- Use write-only `password` field during create/update
- Passwords are **automatically hashed** using Django's default algorithm (PBKDF2)
- Min length: 6 characters (recommended 8+)

### User Permissions
- Dealers authenticate with their username/password
- Can view/update their own dealer profile
- Permission checks can be added via custom backend

### OneToOne Constraint
```python
class Meta:
    constraints = [
        UniqueConstraint(fields=['user'], name='unique_user_dealer')
    ]
```
- Each user can be linked to **at most ONE dealer**
- Prevents duplicate dealer accounts

## API Endpoints

### Dealers CRUD
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dealers/` | List all dealers |
| POST | `/api/dealers/` | Create new dealer with user |
| GET | `/api/dealers/{id}/` | Retrieve dealer details |
| PATCH | `/api/dealers/{id}/` | Update dealer & user info |
| DELETE | `/api/dealers/{id}/` | Delete dealer (removes user if not used) |

### User Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/token/` | Login (get JWT tokens) |
| POST | `/api/token/refresh/` | Refresh access token |
| GET | `/api/users/me/` | Get current user profile |
| PATCH | `/api/users/me/` | Update current user profile |

## Use Cases

### Scenario 1: Create New Dealer with Instant Login
```bash
# Admin creates dealer via API with credentials
POST /api/dealers/
{
  "name": "New Dealer",
  "contact_number": "03001234567",
  "cnic_number": "12345-6789012-3",
  "company": 1,
  "region": 1,
  "username": "new_dealer",
  "email": "dealer@newdealer.com",
  "password": "InitialPass123",
  "first_name": "John",
  "last_name": "Doe"
}

# Dealer immediately logs in
POST /api/token/
{
  "username": "new_dealer",
  "password": "InitialPass123"
}

# Access dealer dashboard
GET /api/dealers/5/
Authorization: Bearer <access_token>
```

### Scenario 2: Convert Existing User to Dealer
```bash
# Admin creates dealer with existing user
POST /api/dealers/
{
  "name": "Khan Enterprises",
  "contact_number": "03009876543",
  "cnic_number": "98765-4321098-7",
  "company": 1,
  "user": 15  # Existing user ID
}

# User already has credentials, can login immediately
```

### Scenario 3: Update Dealer Credentials
```bash
# Change dealer's password
PATCH /api/dealers/5/
{
  "password": "NewPassword789"
}

# Dealer can now login with new password
POST /api/token/
{
  "username": "abc_trader",
  "password": "NewPassword789"
}
```

## Troubleshooting

### "User already exists"
- A user with that username/email already exists
- Either use different username/email or link to existing user via `user` field

### "Dealer with this user already exists"
- That user is already linked to another dealer
- Create a new user or unlink from previous dealer

### "Password does not meet requirements"
- Password must be at least 6 characters
- Recommended: 8+ characters with mix of letters, numbers, symbols

### Dealer can't login
- Verify username and password are correct
- Check `is_active = true` on dealer account
- Ensure associated user account is active
- Check tokens haven't expired (access token: 5 min, refresh: 24 hours)

## Admin Dashboard Features

### Dealer Admin Page
- **List View:**
  - Shows: Name, Username, Email, Phone, Company, Active Status, Created Date
  - Quick search by name, phone, username, email, CNIC
  - Filter by: Active status, Company, Creation date
  - Batch operations support

- **Detail View:**
  - Organized fieldsets:
    - User Account (link to user, auto-generated card code)
    - Dealer Information (name, CNIC, phone, address)
    - Geographic Assignment (company, region, zone, territory)
    - Location Coordinates (latitude, longitude)
    - CNIC Images (collapsible)
    - Status & Audit (created_by, timestamps)

- **User Link:** Click on username → Opens User admin page

### Dealer Creation via Admin
1. Admin → Field Advisory Service → Dealers → Add Dealer
2. Optionally fill user fields (username, email, password, names)
3. Fill dealer info (name, CNIC, phone, company, etc.)
4. Save → User account auto-created if fields provided
5. Send credentials to dealer to login

## Important Notes

- **User-Dealer Relationship:** OneToOne means each user can be ONE dealer
- **Card Code:** Auto-generated SAP identifier (e.g., D00005)
- **Created By:** Tracks which admin created the dealer record
- **CNIC Images:** Required, used for SAP posting and verification
- **Geographic Assignment:** Essential for sales order routing and hierarchy
- **Password Storage:** Uses Django's default PBKDF2-SHA256 algorithm

## Configuration

Default settings in `settings.py`:
```python
# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# SimpleJWT Tokens
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
}
```

## Next Steps

1. ✅ Create dealer with user account
2. ✅ Dealer logs in with username/password
3. ✅ Access protected endpoints with JWT token
4. → Set up dealer-specific permissions (view own sales orders, etc.)
5. → Add dealer dashboard for profile management
6. → Implement dealer-to-farmer relationship
7. → Enable dealer sales order creation

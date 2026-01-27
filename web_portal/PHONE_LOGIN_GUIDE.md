# Phone Number Login Implementation Guide

## Overview
Users can now login using either their **email address** or **phone number**. This works for **all user types**: Farmers, Sales Staff, and Dealers.

## ✅ Implementation Complete

### User Types and Phone Sources

| User Type | Phone Field Source | Login Example |
|-----------|-------------------|---------------|
| **Farmer** | `User.username` (auto-created) | Phone stored as username |
| **Sales Staff** | `SalesStaffProfile.phone_number` | From sales profile |
| **Dealer** | `Dealer.contact_number` or `mobile_phone` | Either phone field works |

## How It Works

### Farmers
- When a farmer is created, a User account is **automatically created**
- Phone number (`primary_phone`) is stored as `User.username`
- Default password: Last 4 digits of CNIC (e.g., if CNIC is 12345-6789012-3, password is "12-3")
- If no CNIC, default password is `farmer1234`
- Farmers can login with phone number directly

### Sales Staff
- Use existing `SalesStaffProfile.phone_number` field
- Can login with either email OR phone number
- Password set during user creation

### Dealers
- Use existing `Dealer.contact_number` or `Dealer.mobile_phone`
- Can login with email OR either phone number
- Password set during user creation

## Migration Guide

### Step 1: Database Migration
```bash
# Create migration for farmer user field
python manage.py makemigrations farmers

# Apply migration
python manage.py migrate farmers
```

### Step 2: Link Existing Farmers to Users
```bash
# Dry run first (see what will happen)
python manage.py link_farmers_to_users --dry-run

# Apply for real
python manage.py link_farmers_to_users
```

This command will:
- ✅ Create User accounts for all farmers
- ✅ Set phone number as username
- ✅ Set default password (CNIC last 4 digits or 'farmer1234')
- ✅ Link farmer to user account
- ✅ Set `is_farmer` flag

### Step 3: Test
```bash
# Run test script
python test_farmer_login.py
```

## API Usage

1. **`accounts/backends.py`** (NEW)
   - Custom authentication backend `EmailOrPhoneBackend`
   - Supports login with email or phone number
   - Automatically falls back to email if phone number not found

2. **`accounts/token_serializers.py`** (UPDATED)
   - Accepts either `email` or `phone_number` field
   - Uses Django's `authenticate()` with custom backend
   - Provides clear error messages

3. **`web_portal/settings.py`** (UPDATED)
   - Added `AUTHENTICATION_BACKENDS` configuration
   - Enables custom authentication backend

4. **`accounts/views.py`** (UPDATED)
   - Enhanced Swagger documentation
   - Shows both login methods with examples

5. **`accounts/admin.py`** (UPDATED)
   - Added help text indicating phone numbers can be used for login
   - Phone number field now visible in list display
   - Phone number searchable in admin interface

## How to Use

### API Endpoint
**POST** `/api/accounts/login/`

### Method 1: Email Login
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

### Method 2: Phone Number Login
```json
{
  "phone_number": "03001234567",
  "password": "your_password"
}
```

### Response (Success - 200)
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": 123,
  "email": "user@example.com",
  "username": "user123",
  "role": "Sales Staff",
  "permissions": [...],
  "companies": [...],
  "default_company": {...}
}
```

### Response (Error - 400)
```json
{
  "message": "Invalid email/phone number or password."
}
```

## Important Notes

### Phone Number Requirements
- Phone number must be registered in the user's **Sales Staff Profile**
- Phone number field: `SalesStaffProfile.phone_number`
- Phone number must match exactly (no formatting applied)
- Only users with Sales Staff profiles can login with phone numbers

### Security Considerations
- Password is always required regardless of login method
- Account must be active (`is_active=True`)
- Error messages are generic to prevent account enumeration
- Case-insensitive email matching

### Validation Rules
- Must provide either `email` OR `phone_number` (at least one required)
- Password field is always required
- Both fields can be provided, but `email` takes precedence

## Admin Interface Updates

### Sales Staff Profile Admin
- **List Display**: Phone number now visible in the list view
- **Search**: Phone numbers are now searchable
- **Help Text**: "📱 Phone number can be used for login instead of email"

### Search Capability
Admins can now search for users by:
- Email
- Username
- Employee code
- **Phone number** (NEW)

## Testing

### Test Case 1: Email Login
```bash
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "test123"
  }'
```

### Test Case 2: Phone Number Login
```bash
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "03001234567",
    "password": "test123"
  }'
```

### Test Case 3: Missing Credentials
```bash
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "password": "test123"
  }'
```
Expected: `{"message": "Email or phone number is required."}`

### Test Case 4: Invalid Phone Number
```bash
curl -X POST http://localhost:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "9999999999",
    "password": "test123"
  }'
```
Expected: `{"message": "Invalid email/phone number or password."}`

## Swagger Documentation

The Swagger UI now shows:
- ✅ Detailed description of both login methods
- ✅ Example requests for email and phone login
- ✅ Field descriptions and requirements
- ✅ Response schema with all returned fields
- ✅ Error response examples

Access Swagger at: `http://localhost:8000/swagger/`

## Migration Required?

**No database migration required** - This feature uses existing fields:
- `User.email` (already exists)
- `SalesStaffProfile.phone_number` (already exists)

## Backward Compatibility

✅ **Fully backward compatible**
- Existing email logins continue to work unchanged
- No breaking changes to API
- Frontend apps using email login require no updates
- New phone login is an additional feature, not a replacement

## Frontend Integration Examples

### JavaScript/TypeScript
```javascript
// Email login
const loginWithEmail = async (email, password) => {
  const response = await fetch('/api/accounts/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return response.json();
};

// Phone login
const loginWithPhone = async (phone_number, password) => {
  const response = await fetch('/api/accounts/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number, password })
  });
  return response.json();
};
```

### React Example
```jsx
const LoginForm = () => {
  const [loginMethod, setLoginMethod] = useState('email');
  const [credential, setCredential] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    const payload = {
      [loginMethod]: credential,  // 'email' or 'phone_number'
      password
    };
    
    const response = await fetch('/api/accounts/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    const data = await response.json();
    if (response.ok) {
      // Store tokens
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
    }
  };

  return (
    <form onSubmit={handleLogin}>
      <select onChange={(e) => setLoginMethod(e.target.value)}>
        <option value="email">Email</option>
        <option value="phone_number">Phone Number</option>
      </select>
      <input
        type="text"
        placeholder={loginMethod === 'email' ? 'Email' : 'Phone Number'}
        value={credential}
        onChange={(e) => setCredential(e.target.value)}
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button type="submit">Login</button>
    </form>
  );
};
```

## Troubleshooting

### Issue: "Invalid email/phone number or password"
**Possible causes:**
1. Phone number doesn't exist in SalesStaffProfile
2. Phone number format doesn't match exactly
3. Wrong password
4. User account is inactive

**Solution:** Verify phone number in Django Admin under Sales Staff Profile

### Issue: Phone number login not working
**Checklist:**
1. ✅ Custom backend added to `settings.py`?
2. ✅ User has a SalesStaffProfile?
3. ✅ Phone number field is filled in the profile?
4. ✅ User account is active?
5. ✅ Password is correct?

### Issue: Email login stopped working
**This shouldn't happen** - Email authentication is still the primary method. If this occurs:
1. Check `AUTHENTICATION_BACKENDS` includes `ModelBackend`
2. Verify email field hasn't been modified
3. Check server logs for errors

## Future Enhancements

Potential improvements:
- [ ] Phone number formatting/normalization
- [ ] Support for international phone formats
- [ ] SMS-based OTP login
- [ ] Phone number verification during signup
- [ ] Rate limiting for failed login attempts
- [ ] Login history tracking

## Support

For issues or questions:
1. Check Django logs: `python manage.py runserver`
2. Verify configuration in Django Admin
3. Test with Swagger UI first
4. Check user's SalesStaffProfile in admin

---

**Last Updated:** January 27, 2026
**Version:** 1.0
**Status:** ✅ Production Ready

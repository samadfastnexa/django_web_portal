# User Profile Update (PATCH) - API Documentation

## Endpoint
```
PATCH /api/users/{id}/
```

## Description
Update user profile with **no required fields**. Send only the fields you want to update.

## Authentication
- **Required**: Yes (Token or Session)
- **Permissions**: Users can only update their own profile. Admins can update any user.

## Content-Type
```
multipart/form-data
```

## Request Examples

### 1. Update Profile Image Only
```bash
curl -X PATCH http://localhost:8000/api/users/1/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -F "profile_image=@/path/to/image.jpg"
```

### 2. Update Name Only
```bash
curl -X PATCH http://localhost:8000/api/users/1/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### 3. Update Multiple Fields
```bash
curl -X PATCH http://localhost:8000/api/users/1/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -F "first_name=John" \
  -F "last_name=Doe" \
  -F "profile_image=@/path/to/photo.png"
```

### 4. Update Password
```bash
curl -X PATCH http://localhost:8000/api/users/1/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "newSecurePassword123"
  }'
```

### 5. Admin: Update User Role
```bash
curl -X PATCH http://localhost:8000/api/users/1/ \
  -H "Authorization: Token ADMIN_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role_id": 2,
    "is_active": true
  }'
```

## Request Body Fields (All Optional)

### User Profile Fields
| Field | Type | Description | Who Can Update |
|-------|------|-------------|----------------|
| `first_name` | string | User's first name | Anyone (own profile) |
| `last_name` | string | User's last name | Anyone (own profile) |
| `profile_image` | file | Profile picture (JPG/PNG, max 5MB) | Anyone (own profile) |
| `password` | string | New password (min 6 chars) | Anyone (own profile) |

### Admin-Only Fields
| Field | Type | Description | Who Can Update |
|-------|------|-------------|----------------|
| `username` | string | Username | Admin/Superuser only |
| `email` | string | Email address | Admin/Superuser only |
| `role_id` | integer | Role ID | Admin/Superuser only |
| `is_active` | boolean | Account active status | Admin/Superuser only |
| `is_staff` | boolean | Staff status | Admin/Superuser only |

### Sales Staff Fields (if `is_sales_staff=true`)
| Field | Type | Description |
|-------|------|-------------|
| `employee_code` | string | Employee code |
| `phone_number` | string | Phone number |
| `address` | string | Address |
| `designation` | string | Job designation |
| `date_of_joining` | date | Joining date (YYYY-MM-DD) |
| `hod` | integer | HOD profile ID |
| `master_hod` | integer | Master HOD profile ID |
| `companies` | array[int] | Company IDs |
| `regions` | array[int] | Region IDs |
| `zones` | array[int] | Zone IDs |
| `territories` | array[int] | Territory IDs |

## Response

### Success (200 OK)
```json
{
  "id": 1,
  "username": "john.doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "profile_image_url": "/media/profile_images/photo.jpg",
  "role": {
    "id": 2,
    "name": "Sales Manager",
    "permissions": [...]
  },
  "is_active": true,
  "is_staff": false,
  "is_sales_staff": true,
  "sales_profile": {
    "employee_code": "EMP001",
    "phone_number": "+1234567890",
    ...
  }
}
```

### Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

#### 400 Bad Request
```json
{
  "profile_image": ["The submitted file is empty."],
  "password": ["This field must be at least 6 characters."]
}
```

## Profile Image Requirements
- **Formats**: JPG, JPEG, PNG
- **Maximum Size**: 5MB
- **Validation**: Automatic format and size validation

## Notes
1. **No fields are required** - send only what you want to update
2. **Non-admin users** cannot update: `username`, `email`, `role_id`, `is_active`, `is_staff`
3. **Password** is automatically hashed when provided
4. **Profile image** returns as `profile_image_url` in response (read-only URL)
5. Use `multipart/form-data` when uploading files, otherwise use `application/json`

## Testing with Postman/Thunder Client
1. Set method to **PATCH**
2. Add Authorization header with your token
3. Select **form-data** body type
4. Add fields you want to update
5. For file upload, select "File" type for `profile_image` field
6. Send request to `/api/users/{your_user_id}/`

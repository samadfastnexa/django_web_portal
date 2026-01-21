# 🎯 Quick Reference: Cart Permissions Setup

## Step-by-Step Guide to Assign Cart Permissions

### 1. Access Django Admin

1. Navigate to: `http://your-domain/admin/`
2. Login with superuser credentials

---

### 2. Assign Permissions to a Role

#### Option A: Create New Role

1. Go to: **Admin → Accounts → Roles → Add Role**
2. Enter Role name (e.g., "Customer", "Sales Agent")
3. Scroll to **Permissions** field
4. Search and select cart permissions:
   - Type "cart" in the filter box
   - Select permissions as needed:
     - ☑️ `cart | cart | Can add products to cart` (`add_to_cart`)
     - ☑️ `cart | cart | Can manage shopping cart` (`manage_cart`)
     - ☑️ `cart | order | Can view order history` (`view_order_history`)
     - ☑️ `cart | order | Can manage orders` (`manage_orders`)
     - ☑️ `cart | order | Can sync orders to SAP` (`sync_orders_to_sap`)
5. Click **Save**

#### Option B: Edit Existing Role

1. Go to: **Admin → Accounts → Roles**
2. Click on the role you want to edit
3. In **Permissions** field, add cart permissions
4. Click **Save**

---

### 3. Assign Role to Users

1. Go to: **Admin → Accounts → Users**
2. Click on a user
3. Select the **Role** from dropdown
4. Click **Save**

---

## 📋 Permission Matrix

| Permission | Code Name | Who Needs It | What It Allows |
|------------|-----------|--------------|----------------|
| Add to Cart | `cart.add_to_cart` | Customers, Sales Agents | Add products to shopping cart |
| Manage Cart | `cart.manage_cart` | Customers, Sales Agents | Update/remove cart items |
| View Order History | `cart.view_order_history` | All authenticated users | View their own orders |
| Manage Orders | `cart.manage_orders` | Admins, Managers | Manage all orders, update status |
| Sync to SAP | `cart.sync_orders_to_sap` | System Admins | Sync orders to SAP B1 |

---

## 🎭 Example Role Configurations

### Customer Role
**Purpose:** Regular customers who can shop and view their orders

**Permissions:**
- ✅ `cart.add_to_cart`
- ✅ `cart.manage_cart`
- ✅ `cart.view_order_history`

**Setup:**
```
Name: Customer
Permissions:
  - cart | cart | Can add products to cart
  - cart | cart | Can manage shopping cart
  - cart | order | Can view order history
```

---

### Sales Agent Role
**Purpose:** Sales representatives who can help customers place orders

**Permissions:**
- ✅ `cart.add_to_cart`
- ✅ `cart.manage_cart`
- ✅ `cart.view_order_history`
- ✅ `cart.manage_orders` (view and update order status)

**Setup:**
```
Name: Sales Agent
Permissions:
  - cart | cart | Can add products to cart
  - cart | cart | Can manage shopping cart
  - cart | order | Can view order history
  - cart | order | Can manage orders
```

---

### Order Manager Role
**Purpose:** Staff who manage orders and payments

**Permissions:**
- ✅ `cart.view_order_history`
- ✅ `cart.manage_orders`
- ✅ `cart.sync_orders_to_sap`

**Setup:**
```
Name: Order Manager
Permissions:
  - cart | order | Can view order history
  - cart | order | Can manage orders
  - cart | order | Can sync orders to SAP
```

---

### Admin Role
**Purpose:** Full access to all cart and order features

**Permissions:**
- ✅ All cart permissions
- ✅ All other system permissions

**Setup:**
```
Name: Admin
Permissions:
  - Select all cart permissions
  - Plus any other required permissions
```

---

## ✅ Verification Steps

### Test if Permissions Work:

1. **Login as test user**
2. **Try to access API endpoints:**

```bash
# Test add to cart (should work if user has permission)
curl -X POST http://localhost:8000/api/cart/cart/add_item/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_item_code": "TEST001",
    "product_name": "Test Product",
    "quantity": 1
  }'
```

3. **Expected Results:**
   - ✅ **With permission:** Returns success message
   - ❌ **Without permission:** Returns 403 Forbidden

---

## 🔍 Troubleshooting

### User can't add to cart

**Check:**
1. User is authenticated
2. User has a role assigned
3. Role has `cart.add_to_cart` permission
4. User's JWT token is valid

**Solution:**
```python
# Django shell
python manage.py shell

from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.get(email='user@example.com')
print(user.role)  # Check if role is assigned
print(user.has_perm('cart.add_to_cart'))  # Should be True
```

---

### Permission not showing in admin

**Check:**
1. Migrations are applied: `python manage.py migrate`
2. App is in `INSTALLED_APPS`
3. Clear browser cache
4. Restart Django server

---

### User sees "Permission denied" error

**Check:**
1. User is logged in
2. JWT token is valid and not expired
3. User's role has the required permission
4. Permission name is correct (e.g., `cart.add_to_cart` not `add_to_cart`)

---

## 🔐 Security Best Practices

1. **Principle of Least Privilege:**
   - Only grant permissions users actually need
   - Don't give `manage_orders` to regular customers

2. **Regular Audits:**
   - Periodically review role permissions
   - Remove permissions from inactive roles

3. **Separate Roles:**
   - Create specific roles for specific functions
   - Don't reuse one role for everything

4. **Test Thoroughly:**
   - Test each role with actual user accounts
   - Verify permissions work as expected

---

## 📞 Quick Commands

```bash
# Create superuser (has all permissions)
python manage.py createsuperuser

# Check if migrations are up to date
python manage.py showmigrations cart

# Test permissions in shell
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(email='test@example.com')
>>> user.has_perm('cart.add_to_cart')
```

---

**Last Updated:** January 19, 2026

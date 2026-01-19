# 🚀 Cart System - Quick Start Guide

## ✅ Installation Complete!

The shopping cart and order management system is now fully installed and configured.

---

## 🎯 Quick Setup (3 Steps)

### Step 1: Verify Installation

All components are already installed:
- ✅ Database migrations applied
- ✅ Cart app registered
- ✅ API endpoints configured
- ✅ Default roles created
- ✅ Permissions assigned

**Check status:**
```bash
python manage.py check
```

---

### Step 2: Assign Roles to Users

1. Open Django Admin: `http://your-domain/admin/`
2. Go to **Accounts → Users**
3. Click on a user
4. Select a **Role**:
   - **Customer** - For regular users who shop
   - **Sales Agent** - For sales staff
   - **Order Manager** - For order management
5. Click **Save**

**Roles Created:**
- ✅ **Customer** (3 permissions)
  - Can add to cart
  - Can manage cart
  - Can view order history

- ✅ **Sales Agent** (4 permissions)
  - All Customer permissions +
  - Can manage orders

- ✅ **Order Manager** (3 permissions)
  - Can view order history
  - Can manage orders
  - Can sync orders to SAP

---

### Step 3: Test the System

#### Option A: Using Swagger UI
1. Navigate to: `http://your-domain/swagger/`
2. Find **cart** endpoints
3. Authorize with your JWT token
4. Test the endpoints

#### Option B: Using curl
```bash
# Get your JWT token first
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Add item to cart
curl -X POST http://localhost:8000/api/cart/cart/add_item/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_item_code": "FG00259",
    "product_name": "Test Product",
    "quantity": 1,
    "unit_price": 1500.00
  }'

# View cart
curl http://localhost:8000/api/cart/cart/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📱 API Endpoints

All endpoints are prefixed with `/api/cart/`

### Cart Operations
```
GET    /api/cart/cart/                      - View cart
POST   /api/cart/cart/add_item/             - Add to cart ⚠️ Requires permission
PATCH  /api/cart/cart/update-item/{id}/     - Update item
DELETE /api/cart/cart/remove-item/{id}/     - Remove item
POST   /api/cart/cart/clear/                - Clear cart
GET    /api/cart/cart/count/                - Get item count
```

### Order Operations
```
GET    /api/cart/orders/                    - List orders
GET    /api/cart/orders/{id}/               - Order details
POST   /api/cart/orders/                    - Create order
PATCH  /api/cart/orders/{id}/update_status/ - Update status ⚠️ Admin only
PATCH  /api/cart/orders/{id}/update_payment/ - Update payment ⚠️ Admin only
GET    /api/cart/orders/statistics/         - Order statistics
```

⚠️ = Requires specific permission

---

## 🔐 Permission Requirements

| Action | Permission Required | Who Has It |
|--------|-------------------|------------|
| Add to Cart | `cart.add_to_cart` | Customer, Sales Agent |
| View Cart | Authenticated user | Everyone logged in |
| Create Order | Authenticated user | Everyone logged in |
| View Own Orders | `cart.view_order_history` | Customer, Sales Agent, Order Manager |
| Manage Orders | `cart.manage_orders` | Sales Agent, Order Manager |
| Sync to SAP | `cart.sync_orders_to_sap` | Order Manager |

---

## 🔄 Automatic Cart Cleanup

Items older than 24 hours are automatically removed.

### Manual Cleanup
```bash
# Clean up expired items
python manage.py cleanup_expired_carts

# Preview what will be deleted
python manage.py cleanup_expired_carts --dry-run

# Custom expiry (48 hours)
python manage.py cleanup_expired_carts --hours 48
```

### Schedule Automatic Cleanup

**Linux/Mac (crontab):**
```bash
# Run daily at midnight
0 0 * * * cd /path/to/project && python manage.py cleanup_expired_carts
```

**Windows (Task Scheduler):**
1. Create new task
2. Trigger: Daily at midnight
3. Action: `python manage.py cleanup_expired_carts`
4. Start in: Project directory

---

## 📖 Documentation Files

📚 **Complete Guides:**
1. **[CART_IMPLEMENTATION_COMPLETE.md](CART_IMPLEMENTATION_COMPLETE.md)** - Implementation summary
2. **[CART_AND_ORDER_SYSTEM_GUIDE.md](CART_AND_ORDER_SYSTEM_GUIDE.md)** - Full API documentation
3. **[CART_PERMISSIONS_QUICK_SETUP.md](CART_PERMISSIONS_QUICK_SETUP.md)** - Permission setup guide

---

## 🎓 Common Tasks

### Add User to Customer Role
```bash
# Django shell
python manage.py shell

from django.contrib.auth import get_user_model
from accounts.models import Role

User = get_user_model()
customer_role = Role.objects.get(name='Customer')

user = User.objects.get(email='user@example.com')
user.role = customer_role
user.save()

print(f"✅ {user.email} is now a Customer")
```

### Check User Permissions
```bash
python manage.py shell

from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.get(email='user@example.com')
print(f"Can add to cart: {user.has_perm('cart.add_to_cart')}")
print(f"All permissions: {list(user.get_all_permissions())}")
```

### View All Cart Permissions
```bash
python manage.py shell

from django.contrib.auth.models import Permission
from cart.models import Cart, Order

cart_perms = Permission.objects.filter(content_type__app_label='cart')
for p in cart_perms:
    print(f"{p.codename}: {p.name}")
```

---

## 🐛 Troubleshooting

### "Permission denied" error
**Problem:** User can't add to cart

**Solution:**
1. Check user has a role assigned
2. Check role has `cart.add_to_cart` permission
3. Verify JWT token is valid

```bash
# Check in shell
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.get(email='user@example.com')
>>> print(user.role)  # Should show a role
>>> print(user.has_perm('cart.add_to_cart'))  # Should be True
```

### Cart items not expiring
**Problem:** Old items still in cart

**Solution:**
Run cleanup command:
```bash
python manage.py cleanup_expired_carts
```

### Can't find cart endpoints in Swagger
**Problem:** Endpoints not showing

**Solution:**
1. Restart Django server
2. Clear browser cache
3. Check URL: `http://localhost:8000/swagger/`

---

## 💡 Best Practices

1. **Assign Roles Properly:**
   - Use "Customer" for regular users
   - Use "Sales Agent" for sales staff
   - Don't give "manage_orders" to customers

2. **Schedule Cleanup:**
   - Set up automated cleanup job
   - Run at least once per day

3. **Test Permissions:**
   - Test each role with actual user
   - Verify permissions work as expected

4. **Monitor Orders:**
   - Check order statistics regularly
   - Update payment status promptly

---

## 🎉 Ready to Use!

The cart system is now ready for production use:
- ✅ All endpoints working
- ✅ Permissions configured
- ✅ Roles created
- ✅ Documentation complete

Start by assigning roles to users and testing the API endpoints!

---

## 📞 Quick Commands Reference

```bash
# Setup
python manage.py migrate                    # Apply migrations
python manage.py setup_cart_roles          # Create default roles

# Testing
python manage.py check                     # Verify installation
python manage.py shell                     # Access Django shell

# Maintenance
python manage.py cleanup_expired_carts     # Clean expired items
python manage.py cleanup_expired_carts --dry-run  # Preview cleanup

# Admin
python manage.py createsuperuser           # Create admin user
```

---

**Last Updated:** January 19, 2026  
**Status:** ✅ READY FOR PRODUCTION

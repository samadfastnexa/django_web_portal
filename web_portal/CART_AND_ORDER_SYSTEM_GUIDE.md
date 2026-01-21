# 🛒 Shopping Cart & Order Management System

## Overview

This comprehensive cart and order management system provides:
- ✅ **Shopping Cart** with role-based permissions
- ✅ **Automatic Cart Expiry** (24 hours)
- ✅ **Order History** with payment tracking
- ✅ **Order Management** with status updates
- ✅ **SAP Integration** ready

---

## 🔐 Permissions

### Custom Permissions Created

The system includes the following permissions:

#### Cart Permissions
```
cart.add_to_cart          - Can add products to cart
cart.manage_cart          - Can manage shopping cart
```

#### Order Permissions
```
cart.view_order_history   - Can view order history
cart.manage_orders        - Can manage orders
cart.sync_orders_to_sap   - Can sync orders to SAP
```

### Assigning Permissions

1. **Via Django Admin:**
   - Go to **Admin → Accounts → Roles**
   - Select or create a role (e.g., "Sales Agent", "Customer")
   - In the **Permissions** field, search for:
     - `cart.add_to_cart` - For users who can add items to cart
     - `cart.manage_cart` - For users who can manage cart
     - `cart.view_order_history` - For users who can view orders
     - `cart.manage_orders` - For admin/staff who manage all orders

2. **Example Role Setup:**

   **Customer Role:**
   - ✅ `cart.add_to_cart`
   - ✅ `cart.manage_cart`
   - ✅ `cart.view_order_history`
   
   **Sales Manager Role:**
   - ✅ `cart.add_to_cart`
   - ✅ `cart.manage_cart`
   - ✅ `cart.view_order_history`
   - ✅ `cart.manage_orders`
   - ✅ `cart.sync_orders_to_sap`

---

## 📡 API Endpoints

### Cart Endpoints

#### 1. Get Cart
```http
GET /api/cart/cart/
```
Returns current user's cart with all active items.

**Response:**
```json
{
  "id": 1,
  "user": 5,
  "items": [
    {
      "id": 1,
      "product_item_code": "FG00259",
      "product_name": "Pesticide XYZ",
      "quantity": 2,
      "unit_price": "1500.00",
      "subtotal": "3000.00",
      "notes": "",
      "is_active": true,
      "is_expired": false,
      "created_at": "2026-01-19T10:30:00Z",
      "updated_at": "2026-01-19T10:30:00Z"
    }
  ],
  "total_items": 1,
  "total_quantity": 2,
  "cart_total": "3000.00",
  "created_at": "2026-01-19T10:30:00Z",
  "updated_at": "2026-01-19T10:30:00Z"
}
```

#### 2. Add to Cart (Requires `add_to_cart` permission)
```http
POST /api/cart/cart/add_item/
```

**Request Body:**
```json
{
  "product_item_code": "FG00259",
  "product_name": "Pesticide XYZ",
  "quantity": 2,
  "unit_price": 1500.00,
  "notes": "Handle with care"
}
```

**Response:**
```json
{
  "message": "Item added to cart",
  "item": {
    "id": 1,
    "product_item_code": "FG00259",
    "product_name": "Pesticide XYZ",
    "quantity": 2,
    "unit_price": "1500.00",
    "subtotal": "3000.00",
    ...
  }
}
```

#### 3. Update Cart Item
```http
PATCH /api/cart/cart/update-item/{item_id}/
```

**Request Body:**
```json
{
  "quantity": 5,
  "notes": "Updated quantity"
}
```

#### 4. Remove from Cart
```http
DELETE /api/cart/cart/remove-item/{item_id}/
```

#### 5. Clear Cart
```http
POST /api/cart/cart/clear/
```

#### 6. Get Cart Count
```http
GET /api/cart/cart/count/
```

**Response:**
```json
{
  "total_items": 3,
  "total_quantity": 8
}
```

---

### Order Endpoints

#### 1. Create Order from Cart
```http
POST /api/cart/orders/
```

**Request Body:**
```json
{
  "shipping_address": "123 Main St, City, Country",
  "notes": "Please deliver before 5 PM"
}
```

**Response:**
```json
{
  "message": "Order created successfully",
  "order": {
    "id": 1,
    "order_number": "ORD-A1B2C3D4-20260119",
    "user": 5,
    "user_email": "user@example.com",
    "status": "pending",
    "payment_status": "unpaid",
    "total_amount": "5000.00",
    "paid_amount": "0.00",
    "items": [...],
    "total_items": 2,
    "total_quantity": 5,
    ...
  }
}
```

#### 2. Get Order History
```http
GET /api/cart/orders/
```

**Response:**
```json
[
  {
    "id": 1,
    "order_number": "ORD-A1B2C3D4-20260119",
    "user_email": "user@example.com",
    "status": "delivered",
    "payment_status": "paid",
    "total_amount": "5000.00",
    "paid_amount": "5000.00",
    "total_items": 2,
    "is_synced_to_sap": true,
    "created_at": "2026-01-18T10:00:00Z"
  }
]
```

#### 3. Get Order Details
```http
GET /api/cart/orders/{id}/
```

#### 4. Update Order Status (Requires `manage_orders` permission)
```http
PATCH /api/cart/orders/{id}/update_status/
```

**Request Body:**
```json
{
  "status": "confirmed"
}
```

**Status Options:**
- `pending`
- `processing`
- `confirmed`
- `shipped`
- `delivered`
- `cancelled`

#### 5. Update Payment (Requires `manage_orders` permission)
```http
PATCH /api/cart/orders/{id}/update_payment/
```

**Request Body:**
```json
{
  "paid_amount": 2500.00,
  "payment_status": "partially_paid"
}
```

**Payment Status Options:**
- `unpaid`
- `partially_paid`
- `paid`
- `refunded`

#### 6. Get Order Statistics
```http
GET /api/cart/orders/statistics/
```

**Response:**
```json
{
  "total_orders": 15,
  "pending_orders": 3,
  "completed_orders": 10,
  "total_spent": 75000.00,
  "unpaid_amount": 5000.00
}
```

---

## 🕐 Automatic Cart Cleanup

Cart items automatically expire after **24 hours**. The system provides a management command for cleanup:

### Manual Cleanup
```bash
python manage.py cleanup_expired_carts
```

### Options
```bash
# Dry run (see what would be deleted without deleting)
python manage.py cleanup_expired_carts --dry-run

# Custom expiry time (default is 24 hours)
python manage.py cleanup_expired_carts --hours 48
```

### Automated Cleanup (Recommended)

Add to your cron job or task scheduler:

**Linux/Mac (crontab):**
```bash
# Run every hour
0 * * * * cd /path/to/project && python manage.py cleanup_expired_carts
```

**Windows (Task Scheduler):**
- Create a scheduled task
- Run: `python manage.py cleanup_expired_carts`
- Schedule: Daily at midnight or hourly

**Using Celery (if installed):**
Create a periodic task in your Celery configuration.

---

## 🔍 Permission Checks in Code

### In Views (Function-Based)
```python
from django.contrib.auth.decorators import permission_required

@permission_required('cart.add_to_cart', raise_exception=True)
def add_to_cart_view(request):
    # Your code here
    pass
```

### In Views (Class-Based)
```python
from rest_framework.permissions import IsAuthenticated
from cart.permissions import CanAddToCart

class AddToCartView(APIView):
    permission_classes = [IsAuthenticated, CanAddToCart]
    
    def post(self, request):
        # Your code here
        pass
```

### Checking Permissions
```python
# Check if user has permission
if request.user.has_perm('cart.add_to_cart'):
    # User can add to cart
    pass

# Check multiple permissions
if request.user.has_perms(['cart.add_to_cart', 'cart.manage_cart']):
    # User has both permissions
    pass
```

---

## 💻 Usage Examples

### Example 1: Add Product to Cart (Frontend/Mobile)

```javascript
// JavaScript/React/React Native
const addToCart = async (product) => {
  const response = await fetch('/api/cart/cart/add_item/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      product_item_code: product.itemCode,
      product_name: product.name,
      quantity: 1,
      unit_price: product.price,
    }),
  });
  
  const data = await response.json();
  console.log(data.message); // "Item added to cart"
};
```

### Example 2: Create Order

```python
# Python/Django
from rest_framework.test import APIClient

client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

# Add items to cart
client.post('/api/cart/cart/add_item/', {
    'product_item_code': 'FG00259',
    'product_name': 'Pesticide XYZ',
    'quantity': 2,
    'unit_price': 1500.00
})

# Create order
response = client.post('/api/cart/orders/', {
    'shipping_address': '123 Main St',
    'notes': 'Urgent delivery'
})

order = response.json()
print(f"Order created: {order['order']['order_number']}")
```

### Example 3: View Order History

```javascript
// JavaScript
const fetchOrderHistory = async () => {
  const response = await fetch('/api/cart/orders/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });
  
  const orders = await response.json();
  
  orders.forEach(order => {
    console.log(`Order: ${order.order_number}`);
    console.log(`Status: ${order.status}`);
    console.log(`Payment: ${order.payment_status}`);
    console.log(`Total: $${order.total_amount}`);
  });
};
```

---

## 🗃️ Database Models

### Cart Model
- `user` - One-to-one relationship with User
- `created_at` - Cart creation timestamp
- `updated_at` - Last update timestamp

### CartItem Model
- `cart` - Foreign key to Cart
- `product_item_code` - SAP Item Code
- `product_name` - Product name
- `quantity` - Quantity in cart
- `unit_price` - Price per unit
- `notes` - Special instructions
- `is_active` - Active status (false when expired/removed)
- `created_at` - When item was added (used for expiry check)

### Order Model
- `user` - User who placed order
- `order_number` - Unique order identifier
- `status` - Order status (pending, processing, confirmed, shipped, delivered, cancelled)
- `payment_status` - Payment status (unpaid, partially_paid, paid, refunded)
- `total_amount` - Total order amount
- `paid_amount` - Amount paid
- `shipping_address` - Delivery address
- `sap_order_id` - SAP Sales Order ID (for integration)
- `is_synced_to_sap` - Sync status

### OrderItem Model
- `order` - Foreign key to Order
- `product_item_code` - SAP Item Code
- `product_name` - Product name (snapshot)
- `quantity` - Quantity ordered
- `unit_price` - Price at time of order
- `subtotal` - Auto-calculated subtotal

---

## ✅ Testing Checklist

1. **Permissions Setup:**
   - [ ] Create role with `add_to_cart` permission
   - [ ] Assign role to test user
   - [ ] Verify permission in admin

2. **Cart Operations:**
   - [ ] Add item to cart
   - [ ] Update item quantity
   - [ ] Remove item from cart
   - [ ] View cart

3. **Order Creation:**
   - [ ] Create order from cart
   - [ ] Verify cart is cleared after order
   - [ ] Check order details

4. **Order Management:**
   - [ ] View order history
   - [ ] Update order status
   - [ ] Update payment information

5. **Automatic Cleanup:**
   - [ ] Run cleanup command
   - [ ] Verify expired items are removed
   - [ ] Test with different time thresholds

---

## 🚀 Next Steps

### For Development:
1. **Integrate with Product Catalog:**
   - Link cart to your SAP products/items
   - Fetch prices from SAP
   
2. **Payment Integration:**
   - Integrate payment gateway
   - Update payment status automatically

3. **SAP Synchronization:**
   - Implement order sync to SAP B1
   - Create sales orders in SAP

4. **Notifications:**
   - Email notifications on order creation
   - SMS notifications for status updates

5. **Frontend Integration:**
   - Build cart UI
   - Create order history page
   - Add checkout flow

---

## 📞 Support

For issues or questions:
1. Check the API documentation at `/swagger/`
2. Review Django admin for permission setup
3. Check server logs for errors

---

**Last Updated:** January 19, 2026

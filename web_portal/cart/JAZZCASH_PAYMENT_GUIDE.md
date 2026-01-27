# JazzCash Payment Integration Guide

Complete guide for implementing product purchases through JazzCash payment gateway with automatic cart expiry.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation & Setup](#installation--setup)
- [API Endpoints](#api-endpoints)
- [Payment Flow](#payment-flow)
- [Cart Auto-Expiry](#cart-auto-expiry)
- [Testing](#testing)
- [Configuration](#configuration)

---

## Overview

This system provides a complete e-commerce solution with:
- Shopping cart management
- JazzCash payment gateway integration
- Automatic cart item expiry (24 hours)
- Order and payment tracking
- Purchase history

## Features

### ✅ Shopping Cart
- Add products to cart
- Update quantities
- Remove items
- Auto-expiry after 24 hours
- Cart total calculation

### ✅ Payment Gateway
- JazzCash integration
- Cash on Delivery support
- Secure payment verification
- Transaction tracking
- Payment callbacks

### ✅ Order Management
- Create orders from cart
- Track order status
- Payment status tracking
- Order history
- SAP integration ready

### ✅ Purchase History
- Complete payment records
- Transaction details
- Refund tracking
- Payment method tracking

---

## Installation & Setup

### 1. Database Migration

Run migrations to create the Payment model:

```bash
python manage.py makemigrations cart
python manage.py migrate
```

### 2. Configuration

Add JazzCash credentials to your `settings.py`:

```python
# JazzCash Payment Gateway Settings
JAZZCASH_MERCHANT_ID = 'your_merchant_id'
JAZZCASH_PASSWORD = 'your_password'
JAZZCASH_INTEGRITY_SALT = 'your_integrity_salt'
JAZZCASH_USE_SANDBOX = True  # Set to False in production

# Site URL for payment callbacks
SITE_URL = 'http://localhost:8000'  # Update for production
```

### 3. Schedule Cart Cleanup

Add cron job to clean expired cart items:

**Linux/Mac (crontab):**
```bash
# Run every hour
0 * * * * cd /path/to/project && python manage.py clean_expired_carts
```

**Windows (Task Scheduler):**
```powershell
# Create scheduled task to run hourly
python manage.py clean_expired_carts
```

**Or use Django-Celery for background tasks:**
```python
# In celery.py
from celery import shared_task
from cart.models import Cart

@shared_task
def clean_expired_carts():
    from django.core.management import call_command
    call_command('clean_expired_carts')
```

---

## API Endpoints

### Cart Endpoints

#### 1. Get Cart
```http
GET /api/cart/cart/
```

**Response:**
```json
{
  "id": 1,
  "user": 5,
  "items": [
    {
      "id": 10,
      "product_item_code": "FG00259",
      "product_name": "Wheat Seeds",
      "quantity": 2,
      "unit_price": "1500.00",
      "subtotal": "3000.00",
      "is_expired": false,
      "created_at": "2026-01-23T10:30:00Z"
    }
  ],
  "total_items": 1,
  "total_quantity": 2,
  "cart_total": "3000.00"
}
```

#### 2. Add to Cart
```http
POST /api/cart/cart/add_item/
```

**Request Body:**
```json
{
  "product_item_code": "FG00259",
  "product_name": "Wheat Seeds",
  "quantity": 2,
  "unit_price": "1500.00",
  "notes": "Premium quality"
}
```

#### 3. Update Cart Item
```http
PATCH /api/cart/cart/update-item/{item_id}/
```

**Request Body:**
```json
{
  "quantity": 3,
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

### Order Endpoints

#### 1. Create Order from Cart
```http
POST /api/cart/orders/
```

**Request Body:**
```json
{
  "shipping_address": "House 123, Street 5, Lahore",
  "notes": "Please deliver in morning"
}
```

**Response:**
```json
{
  "message": "Order created successfully",
  "order": {
    "id": 15,
    "order_number": "ORD-A1B2C3D4-20260123",
    "status": "pending",
    "payment_status": "unpaid",
    "total_amount": "3000.00",
    "items": [...],
    "created_at": "2026-01-23T10:30:00Z"
  }
}
```

#### 2. Get Order History
```http
GET /api/cart/orders/
```

#### 3. Get Order Details
```http
GET /api/cart/orders/{order_id}/
```

### Payment Endpoints

#### 1. Initiate Payment
```http
POST /api/cart/payments/initiate/
```

**Request Body (JazzCash):**
```json
{
  "order_id": 15,
  "payment_method": "jazzcash",
  "amount": "3000.00",
  "customer_phone": "03001234567",
  "customer_email": "customer@example.com"
}
```

**Response:**
```json
{
  "message": "Payment initiated successfully",
  "payment_id": 25,
  "transaction_id": "TXN-A1B2C3D4E5F6",
  "payment_method": "jazzcash",
  "jazzcash_payment_url": "https://sandbox.jazzcash.com.pk/...",
  "jazzcash_form_data": {
    "pp_Version": "1.1",
    "pp_TxnType": "MWALLET",
    "pp_MerchantID": "MC12345",
    ...
  },
  "amount": "3000.00"
}
```

**Request Body (Cash on Delivery):**
```json
{
  "order_id": 15,
  "payment_method": "cash_on_delivery",
  "amount": "3000.00"
}
```

#### 2. Get Payment History
```http
GET /api/cart/payments/
```

#### 3. Verify Payment
```http
POST /api/cart/payments/verify/
```

**Request Body:**
```json
{
  "transaction_id": "TXN-A1B2C3D4E5F6"
}
```

#### 4. JazzCash Callback (Internal)
```http
POST /api/cart/payments/jazzcash/callback/
```
*This endpoint is called by JazzCash gateway automatically*

#### 5. JazzCash Return URL (Internal)
```http
GET /api/cart/payments/jazzcash/return/
```
*User is redirected here after payment*

---

## Payment Flow

### JazzCash Payment Flow

```
1. User adds products to cart
   ↓
2. User creates order from cart
   ↓
3. User initiates JazzCash payment
   POST /api/cart/payments/initiate/
   ↓
4. Frontend displays JazzCash payment form
   Submit form data to jazzcash_payment_url
   ↓
5. User completes payment on JazzCash
   ↓
6. JazzCash calls callback endpoint
   POST /api/cart/payments/jazzcash/callback/
   (Payment verified and order updated)
   ↓
7. User redirected to return URL
   GET /api/cart/payments/jazzcash/return/
   (Shows payment success/failure page)
```

### Frontend Integration Example

```html
<!-- After initiating payment, render this form -->
<form id="jazzcashForm" method="POST" action="{{ jazzcash_payment_url }}">
  <input type="hidden" name="pp_Version" value="{{ payment_data.pp_Version }}">
  <input type="hidden" name="pp_TxnType" value="{{ payment_data.pp_TxnType }}">
  <input type="hidden" name="pp_MerchantID" value="{{ payment_data.pp_MerchantID }}">
  <input type="hidden" name="pp_Password" value="{{ payment_data.pp_Password }}">
  <input type="hidden" name="pp_TxnRefNo" value="{{ payment_data.pp_TxnRefNo }}">
  <input type="hidden" name="pp_Amount" value="{{ payment_data.pp_Amount }}">
  <input type="hidden" name="pp_TxnCurrency" value="{{ payment_data.pp_TxnCurrency }}">
  <input type="hidden" name="pp_TxnDateTime" value="{{ payment_data.pp_TxnDateTime }}">
  <input type="hidden" name="pp_BillReference" value="{{ payment_data.pp_BillReference }}">
  <input type="hidden" name="pp_Description" value="{{ payment_data.pp_Description }}">
  <input type="hidden" name="pp_TxnExpiryDateTime" value="{{ payment_data.pp_TxnExpiryDateTime }}">
  <input type="hidden" name="pp_ReturnURL" value="{{ payment_data.pp_ReturnURL }}">
  <input type="hidden" name="pp_SecureHash" value="{{ payment_data.pp_SecureHash }}">
  <input type="hidden" name="pp_MobileNumber" value="{{ payment_data.pp_MobileNumber }}">
  
  <button type="submit">Proceed to Payment</button>
</form>

<script>
  // Auto-submit the form
  document.getElementById('jazzcashForm').submit();
</script>
```

---

## Cart Auto-Expiry

### How It Works

Cart items automatically expire after **24 hours** from when they were added.

### Manual Cleanup

Run the cleanup command manually:

```bash
# Clean items older than 24 hours
python manage.py clean_expired_carts

# Dry run (see what would be deleted)
python manage.py clean_expired_carts --dry-run

# Custom expiry time (e.g., 48 hours)
python manage.py clean_expired_carts --hours=48
```

### Automatic Cleanup

The system has multiple cleanup mechanisms:

1. **On Cart Access**: Expired items are cleaned when user accesses their cart
2. **Scheduled Task**: Run cleanup command via cron/scheduler
3. **Model Method**: `cart.clear_expired_items()` can be called anytime

---

## Testing

### Test with JazzCash Sandbox

1. Use sandbox credentials from JazzCash
2. Test mobile number: Use any valid format (03xxxxxxxxx)
3. Payment will not deduct real money

### Test Scenarios

#### 1. Add to Cart and Create Order
```bash
# Add item to cart
curl -X POST http://localhost:8000/api/cart/cart/add_item/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_item_code": "FG00259",
    "product_name": "Test Product",
    "quantity": 1,
    "unit_price": "100.00"
  }'

# Create order
curl -X POST http://localhost:8000/api/cart/orders/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": "Test Address"
  }'
```

#### 2. Initiate JazzCash Payment
```bash
curl -X POST http://localhost:8000/api/cart/payments/initiate/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": 1,
    "payment_method": "jazzcash",
    "amount": "100.00",
    "customer_phone": "03001234567"
  }'
```

#### 3. Test Cart Expiry
```bash
# Add item and wait 24 hours, or modify created_at manually in DB
# Then access cart - expired items will be automatically removed
curl -X GET http://localhost:8000/api/cart/cart/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Configuration

### Settings

```python
# settings.py

# JazzCash Configuration
JAZZCASH_MERCHANT_ID = env('JAZZCASH_MERCHANT_ID', default='MC12345')
JAZZCASH_PASSWORD = env('JAZZCASH_PASSWORD', default='test_password')
JAZZCASH_INTEGRITY_SALT = env('JAZZCASH_INTEGRITY_SALT', default='test_salt')
JAZZCASH_USE_SANDBOX = env.bool('JAZZCASH_USE_SANDBOX', default=True)

# Site Configuration
SITE_URL = env('SITE_URL', default='http://localhost:8000')

# Cart Configuration
CART_EXPIRY_HOURS = 24  # Auto-expire cart items after 24 hours
```

### Environment Variables (.env)

```env
JAZZCASH_MERCHANT_ID=your_merchant_id
JAZZCASH_PASSWORD=your_password
JAZZCASH_INTEGRITY_SALT=your_salt
JAZZCASH_USE_SANDBOX=True
SITE_URL=http://localhost:8000
```

---

## Permissions

### Required Permissions

- `cart.add_to_cart` - Add products to cart
- `cart.manage_cart` - Manage shopping cart
- `cart.view_order_history` - View order history
- `cart.manage_orders` - Manage all orders
- `cart.process_payments` - Process payments
- `cart.refund_payments` - Refund payments

### Grant Permissions

```python
from django.contrib.auth.models import Permission
from accounts.models import User

user = User.objects.get(email='user@example.com')

# Grant cart permissions
perms = [
    'cart.add_to_cart',
    'cart.manage_cart',
    'cart.view_order_history',
]

for perm_codename in perms:
    app_label, codename = perm_codename.split('.')
    perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
    user.user_permissions.add(perm)
```

---

## Support & Troubleshooting

### Common Issues

**1. Cart items not expiring**
- Run cleanup command manually
- Check if cron job is configured
- Verify timezone settings

**2. JazzCash payment not working**
- Verify credentials in settings
- Check callback URL is accessible
- Review JazzCash sandbox documentation

**3. Payment verification failed**
- Check secure hash calculation
- Verify integrity salt matches
- Review JazzCash response codes

### Logs

Check logs for payment processing:

```python
# In Django shell
from cart.models import Payment

# Get failed payments
Payment.objects.filter(status='failed')

# Check raw responses
for p in Payment.objects.filter(status='failed'):
    print(p.raw_response)
```

---

## Video Reference

YouTube Tutorial: https://www.youtube.com/watch?v=Fsz-O9_1JAU

---

## Next Steps

1. ✅ Run migrations
2. ✅ Configure JazzCash credentials
3. ✅ Set up cart cleanup cron job
4. ✅ Test payment flow in sandbox
5. ✅ Implement frontend integration
6. ✅ Go live with production credentials

---

**Created:** January 23, 2026
**Author:** Tarzan Development Team
**Version:** 1.0

# ✅ Testing Checklist - JazzCash Payment System

Complete testing checklist to verify all functionality before deployment.

## Pre-Testing Setup

- [ ] Database migrations applied (`python manage.py migrate cart`)
- [ ] JazzCash settings configured in `settings.py`
- [ ] Superuser created for admin access
- [ ] Test users created with proper permissions
- [ ] Development server running (`python manage.py runserver`)

---

## 1️⃣ Cart Functionality Tests

### Add to Cart
- [ ] Can add product with valid data
- [ ] Quantity updates if same product added twice
- [ ] Unit price is stored correctly
- [ ] Notes field works
- [ ] Returns proper error with invalid product code
- [ ] Returns proper error with negative quantity
- [ ] Requires authentication

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/cart/cart/add_item/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"product_item_code":"TEST001","product_name":"Test Product","quantity":2,"unit_price":"100.00"}'
```

### View Cart
- [ ] Returns current user's cart
- [ ] Shows all active items
- [ ] Calculates totals correctly
- [ ] Hides expired items
- [ ] Returns empty cart for new users

**Test Command:**
```bash
curl -X GET http://localhost:8000/api/cart/cart/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Cart Item
- [ ] Can update quantity
- [ ] Can update notes
- [ ] Returns error for non-existent item
- [ ] Returns error for other user's items
- [ ] Validates minimum quantity

**Test Command:**
```bash
curl -X PATCH http://localhost:8000/api/cart/cart/update-item/1/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity":5}'
```

### Remove from Cart
- [ ] Can remove item
- [ ] Item marked as inactive (not deleted)
- [ ] Returns error for non-existent item
- [ ] Cannot remove other user's items

**Test Command:**
```bash
curl -X DELETE http://localhost:8000/api/cart/cart/remove-item/1/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Clear Cart
- [ ] Marks all items as inactive
- [ ] Confirms successful clear
- [ ] Works with empty cart

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/cart/cart/clear/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Cart Count
- [ ] Returns correct item count
- [ ] Returns correct total quantity
- [ ] Excludes inactive items

**Test Command:**
```bash
curl -X GET http://localhost:8000/api/cart/cart/count/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 2️⃣ Order Functionality Tests

### Create Order
- [ ] Creates order from cart items
- [ ] Generates unique order number
- [ ] Clears cart after order creation
- [ ] Calculates total amount correctly
- [ ] Stores shipping address
- [ ] Stores order notes
- [ ] Returns error if cart is empty
- [ ] Sets initial status as 'pending'
- [ ] Sets payment status as 'unpaid'

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/cart/orders/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"shipping_address":"123 Test Street, Lahore","notes":"Test order"}'
```

### View Order History
- [ ] Returns user's orders only (non-admin)
- [ ] Returns all orders (admin)
- [ ] Orders sorted by creation date (newest first)
- [ ] Includes order items
- [ ] Shows payment status
- [ ] Shows order status

**Test Command:**
```bash
curl -X GET http://localhost:8000/api/cart/orders/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### View Order Details
- [ ] Returns complete order information
- [ ] Includes all order items
- [ ] Shows user information
- [ ] Shows payment details
- [ ] Returns 404 for non-existent order
- [ ] Cannot view other user's orders (non-admin)

**Test Command:**
```bash
curl -X GET http://localhost:8000/api/cart/orders/1/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Order Status (Admin Only)
- [ ] Admin can update status
- [ ] Regular user cannot update
- [ ] Validates status choices
- [ ] Sets completed_at when status is 'delivered'

**Test Command:**
```bash
curl -X PATCH http://localhost:8000/api/cart/orders/1/update_status/ \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"confirmed"}'
```

### Order Statistics
- [ ] Returns total orders count
- [ ] Returns pending orders count
- [ ] Returns completed orders count
- [ ] Calculates total spent
- [ ] Calculates unpaid amount

**Test Command:**
```bash
curl -X GET http://localhost:8000/api/cart/orders/statistics/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 3️⃣ Payment Functionality Tests

### Initiate JazzCash Payment
- [ ] Creates payment record
- [ ] Generates unique transaction ID
- [ ] Returns JazzCash form data
- [ ] Returns payment URL
- [ ] Validates order exists
- [ ] Validates order belongs to user
- [ ] Prevents payment for already paid orders
- [ ] Validates phone number format
- [ ] Stores customer information

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/cart/payments/initiate/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id":1,
    "payment_method":"jazzcash",
    "amount":"1500.00",
    "customer_phone":"03001234567",
    "customer_email":"test@example.com"
  }'
```

### Initiate Cash on Delivery
- [ ] Creates payment record
- [ ] Marks payment as completed
- [ ] Updates order status to confirmed
- [ ] Doesn't require phone number

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/cart/payments/initiate/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id":1,
    "payment_method":"cash_on_delivery",
    "amount":"1500.00"
  }'
```

### View Payment History
- [ ] Returns user's payments (regular user)
- [ ] Returns all payments (admin)
- [ ] Shows payment status
- [ ] Shows payment method
- [ ] Shows transaction details

**Test Command:**
```bash
curl -X GET http://localhost:8000/api/cart/payments/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Verify Payment
- [ ] Retrieves payment by transaction ID
- [ ] Returns current payment status
- [ ] User can only verify own payments

**Test Command:**
```bash
curl -X POST http://localhost:8000/api/cart/payments/verify/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"TXN-ABC123"}'
```

### JazzCash Callback (Automated Test)
- [ ] Accepts POST from JazzCash
- [ ] Verifies secure hash
- [ ] Updates payment status
- [ ] Updates order status
- [ ] Marks payment as completed (success)
- [ ] Marks payment as failed (failure)
- [ ] Stores JazzCash response
- [ ] Stores transaction ID
- [ ] Returns success/failure response

**Manual Test:**
1. Initiate payment
2. Submit JazzCash form
3. Complete payment on JazzCash
4. Verify callback is received
5. Check payment status updated in admin

### JazzCash Return URL
- [ ] Displays success page (successful payment)
- [ ] Displays failure page (failed payment)
- [ ] Shows transaction details
- [ ] Shows order information
- [ ] Provides navigation buttons

**Manual Test:**
1. Complete payment flow
2. Verify redirect to return URL
3. Check page displays correctly
4. Test navigation buttons

---

## 4️⃣ Cart Auto-Expiry Tests

### Automatic Expiry on Access
- [ ] Expired items marked inactive when cart accessed
- [ ] Only items older than 24 hours affected
- [ ] Active items remain active
- [ ] Works correctly with empty cart

**Test:**
1. Add items to cart
2. Manually set created_at to >24 hours ago in database
3. Access cart
4. Verify items marked as inactive

### Manual Cleanup Command
- [ ] Command runs without errors
- [ ] Finds expired items correctly
- [ ] Marks items as inactive
- [ ] Shows count of cleaned items
- [ ] Dry-run mode works correctly
- [ ] Custom hours parameter works

**Test Commands:**
```bash
# Dry run
python manage.py clean_expired_carts --dry-run

# Actual cleanup
python manage.py clean_expired_carts

# Custom time
python manage.py clean_expired_carts --hours=48
```

### Model Method
- [ ] `cart.clear_expired_items()` works
- [ ] Returns count of expired items
- [ ] Updates is_active field
- [ ] Doesn't affect active items

**Test in Django Shell:**
```python
from cart.models import Cart
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
cart = Cart.objects.get(user=user)
count = cart.clear_expired_items()
print(f"Cleaned {count} expired items")
```

---

## 5️⃣ Admin Interface Tests

### Cart Admin
- [ ] Can view all carts
- [ ] Can search by user
- [ ] Shows total items
- [ ] Shows timestamps

### Cart Item Admin
- [ ] Can view all cart items
- [ ] Can filter by active/inactive
- [ ] Can search by product
- [ ] Shows expiry status
- [ ] Can edit items

### Order Admin
- [ ] Can view all orders
- [ ] Can filter by status
- [ ] Can filter by payment status
- [ ] Can search by order number
- [ ] Can edit order status
- [ ] Shows order items inline
- [ ] Order number is read-only

### Order Item Admin
- [ ] Can view all order items
- [ ] Can search by order/product
- [ ] Subtotal calculated automatically
- [ ] Cannot edit subtotal

### Payment Admin
- [ ] Can view all payments
- [ ] Can filter by method/status
- [ ] Can search by transaction ID
- [ ] Shows JazzCash details
- [ ] Cannot delete completed payments
- [ ] Raw response visible
- [ ] Transaction ID is read-only

---

## 6️⃣ Security Tests

### Authentication
- [ ] Unauthenticated users cannot access cart
- [ ] Unauthenticated users cannot create orders
- [ ] Unauthenticated users cannot initiate payments
- [ ] JazzCash callbacks work without authentication

### Authorization
- [ ] Users can only see their own cart
- [ ] Users can only see their own orders
- [ ] Users can only see their own payments
- [ ] Admin can see all data
- [ ] Proper permission checks for admin actions

### Data Validation
- [ ] Negative quantities rejected
- [ ] Invalid payment methods rejected
- [ ] Invalid phone numbers rejected
- [ ] Missing required fields rejected
- [ ] SQL injection attempts blocked
- [ ] XSS attempts sanitized

### JazzCash Security
- [ ] Secure hash calculated correctly
- [ ] Invalid hash rejected in callback
- [ ] Tampered data rejected
- [ ] HMAC-SHA256 used for hashing

---

## 7️⃣ Edge Cases

- [ ] Creating order with empty cart shows error
- [ ] Paying for non-existent order shows error
- [ ] Paying for already paid order shows error
- [ ] Adding item to cart twice updates quantity
- [ ] Cart handles decimal prices correctly
- [ ] Order total matches sum of items
- [ ] Payment amount matches order total
- [ ] Timezone handling works correctly
- [ ] Unicode characters in product names work
- [ ] Long addresses handled properly

---

## 8️⃣ Integration Tests

### Complete Purchase Flow
- [ ] Add multiple items to cart
- [ ] Update quantities
- [ ] Remove some items
- [ ] Create order
- [ ] Verify cart cleared
- [ ] Initiate payment
- [ ] Complete payment (sandbox)
- [ ] Verify payment callback
- [ ] Check order status updated
- [ ] Check payment record created

**Test Scenario:**
1. User adds 3 products to cart
2. Updates quantity of one product
3. Removes one product
4. Creates order from cart (2 items remaining)
5. Initiates JazzCash payment
6. Completes payment in sandbox
7. Verify all statuses updated correctly

---

## 9️⃣ Performance Tests

- [ ] Cart loads quickly (<200ms)
- [ ] Order creation is fast (<500ms)
- [ ] Payment initiation is fast (<500ms)
- [ ] Cleanup command handles large datasets
- [ ] Database queries optimized (use select_related)
- [ ] No N+1 query problems

---

## 🔟 Error Handling Tests

### Expected Errors
- [ ] Proper 400 for invalid data
- [ ] Proper 401 for unauthenticated
- [ ] Proper 403 for unauthorized
- [ ] Proper 404 for not found
- [ ] Proper error messages returned
- [ ] Errors logged correctly

### Unexpected Errors
- [ ] Database connection failure handled
- [ ] JazzCash API timeout handled
- [ ] Invalid JazzCash response handled
- [ ] Missing configuration handled gracefully

---

## Documentation Tests

- [ ] All API endpoints documented
- [ ] Swagger/OpenAPI docs work
- [ ] Quick start guide accurate
- [ ] Full guide comprehensive
- [ ] Code examples work
- [ ] Architecture diagrams clear

---

## Final Checklist Before Production

- [ ] All tests passed
- [ ] Production JazzCash credentials configured
- [ ] JAZZCASH_USE_SANDBOX = False
- [ ] SITE_URL updated to production domain
- [ ] SSL certificate installed
- [ ] Logging configured
- [ ] Cart cleanup scheduled (cron/celery)
- [ ] Admin users configured
- [ ] Permissions assigned correctly
- [ ] Database backed up
- [ ] Monitoring set up
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Load testing completed
- [ ] Security audit passed

---

## Test Results Template

```
Test Date: _________________
Tester: ____________________
Environment: _______________

Results:
✅ Cart Functionality: PASS / FAIL
✅ Order Management: PASS / FAIL
✅ Payment Processing: PASS / FAIL
✅ Cart Expiry: PASS / FAIL
✅ Admin Interface: PASS / FAIL
✅ Security: PASS / FAIL
✅ Edge Cases: PASS / FAIL
✅ Integration: PASS / FAIL

Issues Found:
1. ___________________________
2. ___________________________
3. ___________________________

Notes:
_______________________________
_______________________________
```

---

**Testing Status:** 🔲 Not Started / 🔄 In Progress / ✅ Complete

**Ready for Production:** 🔲 NO / ✅ YES

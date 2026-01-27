# 🚀 JazzCash Payment Quick Start

Get up and running with JazzCash payments in 5 minutes!

## Step 1: Run Migrations

```bash
cd django_web_portal/web_portal
python manage.py migrate cart
```

## Step 2: Configure Settings

Add to `web_portal/settings.py`:

```python
# JazzCash Settings
JAZZCASH_MERCHANT_ID = 'MC12345'  # Get from JazzCash
JAZZCASH_PASSWORD = 'your_password'
JAZZCASH_INTEGRITY_SALT = 'your_salt'
JAZZCASH_USE_SANDBOX = True  # For testing
SITE_URL = 'http://localhost:8000'
```

## Step 3: Test the Flow

### Add to Cart
```bash
curl -X POST http://localhost:8000/api/cart/cart/add_item/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_item_code": "TEST001",
    "product_name": "Test Product",
    "quantity": 1,
    "unit_price": "100.00"
  }'
```

### Create Order
```bash
curl -X POST http://localhost:8000/api/cart/orders/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": "Test Address",
    "notes": "Test order"
  }'
```

### Initiate Payment
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

## Step 4: Setup Cart Auto-Cleanup

### Option A: Cron Job (Linux/Mac)
```bash
# Run every hour
0 * * * * cd /path/to/project && python manage.py clean_expired_carts
```

### Option B: Windows Task Scheduler
Create a scheduled task to run:
```
python manage.py clean_expired_carts
```

### Option C: Manual Cleanup
```bash
python manage.py clean_expired_carts
```

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/cart/cart/` | GET | Get current cart |
| `/api/cart/cart/add_item/` | POST | Add item to cart |
| `/api/cart/cart/update-item/{id}/` | PATCH | Update quantity |
| `/api/cart/cart/remove-item/{id}/` | DELETE | Remove item |
| `/api/cart/orders/` | POST | Create order |
| `/api/cart/orders/` | GET | Get order history |
| `/api/cart/payments/initiate/` | POST | Start payment |
| `/api/cart/payments/` | GET | Payment history |

## Payment Methods Supported

- ✅ **JazzCash** - Mobile wallet payment
- ✅ **Cash on Delivery** - Pay on delivery
- 🔜 **EasyPaisa** - Coming soon
- 🔜 **Bank Transfer** - Coming soon

## Key Features

✅ **Cart Auto-Expiry**: Items removed after 24 hours  
✅ **Payment Tracking**: Complete transaction history  
✅ **Order Management**: Track order status  
✅ **Secure Payments**: Hash verification for JazzCash  
✅ **Admin Interface**: Manage payments in Django admin  

## Next Steps

1. Read full documentation: `JAZZCASH_PAYMENT_GUIDE.md`
2. Configure production settings
3. Test payment flow
4. Set up cart cleanup automation
5. Customize payment result page

## Need Help?

- Check logs: `logs/payments.log`
- View payments in Django admin: `/admin/cart/payment/`
- Test with sandbox credentials first
- Review JazzCash documentation

---

**Ready to go live?**
1. Update `JAZZCASH_USE_SANDBOX = False`
2. Add production credentials
3. Update `SITE_URL` to your domain
4. Test thoroughly before launch!

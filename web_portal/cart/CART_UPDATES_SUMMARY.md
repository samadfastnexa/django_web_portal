# Cart API Updates Summary

## Overview
Updated cart APIs to include cart_id, user_id, product images, timestamps, and added a new checkout endpoint with normalized data.

## Changes Made

### 1. **Cart Detail Endpoint with Product Images**
- **Endpoint**: `GET /api/cart/cart/`
- **Updates**:
  - Added `cart_id` to response
  - Added `user_id` to response
  - Added product image URLs for each cart item:
    - `product_image_url`: Main product image
    - `product_description_urdu_url`: Urdu description image
  - Images are fetched from `/media/product_images/{database}/{item_code}.jpg`
  - Database context can be passed (default: '4B-BIO')

### 2. **Clear Cart Endpoint**
- **Endpoint**: `POST /api/cart/cart/clear/`
- **Updates**:
  - Response now includes:
    - `cart_id`
    - `user_id`
    - `cleared_at` timestamp

### 3. **NEW: Checkout API**
- **Endpoint**: `POST /api/cart/cart/checkout/`
- **Description**: Convert all cart products to one order with normalized cart and consumer details
- **Request Body**:
  ```json
  {
    "customer_name": "Optional customer name",
    "customer_email": "Optional customer email",
    "customer_phone": "Optional phone number",
    "shipping_address": "Optional shipping address",
    "notes": "Optional order notes",
    "database": "4B-BIO or 4B-ORANG (optional, default: 4B-BIO)"
  }
  ```
- **Response**:
  ```json
  {
    "message": "Order created successfully",
    "order": {
      // Full order details with OrderSerializer
      "order_number": "ORD-XXXXXXXX-20260206",
      "status": "pending",
      "total_amount": "1500.00",
      ...
    },
    "cart_details": {
      "cart_id": 123,
      "total_items": 3,
      "total_quantity": 5,
      "items": [
        {
          "product_item_code": "FG00259",
          "product_name": "Product Name",
          "quantity": 2,
          "unit_price": "500.00",
          "subtotal": "1000.00",
          "product_image_url": "/media/product_images/4B-BIO/FG00259.jpg",
          "product_description_urdu_url": "/media/product_images/4B-BIO/FG00259-urdu.jpg"
        }
      ]
    },
    "consumer_details": {
      "user_id": 456,
      "email": "user@example.com",
      "name": "Customer Name",
      "phone": "03001234567",
      "shipping_address": "Delivery address"
    }
  }
  ```

### 4. **Order Status Choices Updated**
- Changed from `processing` to `in_progress`
- **Available statuses**:
  - `pending` - Default status for new orders
  - `in_progress` - Order is being processed
  - `confirmed` - Order confirmed
  - `shipped` - Order shipped
  - `delivered` - Order delivered
  - `cancelled` - Order cancelled

### 5. **All Cart Endpoints Now Include**:
- `user_id` in all responses
- `cart_id` where applicable
- `created_at` and `updated_at` timestamps (already in serializers)
- Timestamps for actions (e.g., `cleared_at`, `removed_at`, `updated_at`)

## Updated Endpoints

### Add to Cart
- **Endpoint**: `POST /api/cart/cart/add_item/`
- **Response includes**: `cart_id`, `user_id`, `created_at`/`updated_at`

### Update Cart Item
- **Endpoint**: `PATCH /api/cart/cart/update-item/{item_id}/`
- **Response includes**: `cart_id`, `user_id`, `updated_at`

### Remove Cart Item
- **Endpoint**: `DELETE /api/cart/cart/remove-item/{item_id}/`
- **Response includes**: `cart_id`, `user_id`, `removed_at`

### Get Cart Count
- **Endpoint**: `GET /api/cart/cart/count/`
- **Response includes**: `cart_id`, `user_id`, `total_items`, `total_quantity`

## Serializers Updated

### CartItemSerializer
- Added `product_image_url` (read-only)
- Added `product_description_urdu_url` (read-only)
- Timestamps already included: `created_at`, `updated_at`

### CartSerializer
- Added `cart_id` (alias for `id`)
- Added `user_id` (from `user.id`)
- Timestamps already included: `created_at`, `updated_at`

### CheckoutSerializer (New)
- Handles consumer details (name, email, phone)
- Handles shipping address
- Handles order notes
- Supports database context for product images

## Migration Created
- **File**: `cart/migrations/0003_alter_order_status.py`
- **Changes**: Updates Order.status choices (processing → in_progress)

## Testing

To test the new checkout endpoint:
```bash
POST /api/cart/cart/checkout/
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "customer_phone": "03001234567",
  "shipping_address": "123 Main St, Lahore",
  "notes": "Please deliver before 5 PM",
  "database": "4B-BIO"
}
```

## Notes
- Product images are constructed based on item codes
- Default database is '4B-BIO', can be changed to '4B-ORANG'
- All cart operations now return comprehensive metadata
- Checkout creates orders with 'pending' status by default
- Cart is automatically cleared after successful checkout

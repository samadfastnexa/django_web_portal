# Product Images - Quick Reference

## ⚙️ Configuration

### Base URL Setting
To change the base URL for full image URLs, update `.env` file:
```
BASE_URL=http://localhost:8000          # Development
BASE_URL=https://yourdomain.com         # Production
BASE_URL=http://192.168.18.222:8000     # Local Network
```

## 📁 Folder Structure
```
media/product_images/
├── 4B-BIO/       → Images for 4B-BIO_APP database
└── 4B-ORANG/     → Images for 4B-ORANG_APP database
```

## 🏷️ Image Naming
**Use exact filename from SAP!**

Format: `{ItemCode}-{ProductName}.{extension}`

Examples from SAP:
- `FG00292-Gabru-Df.jpg`
- `FG00292-Gabru-DF-urdu.jpg`

The filename comes from SAP's `Product_Image` field.

## 🌐 API Endpoint

**URL:** `GET /sap/products-catalog/`

**Parameters:**
- `database` (optional): `4B-BIO_APP` or `4B-ORANG_APP`

**Examples:**
```bash
# 4B-BIO database
GET /sap/products-catalog/?database=4B-BIO_APP

# 4B-ORANG database
GET /sap/products-catalog/?database=4B-ORANG_APP

# Default database
GET /sap/products-catalog/
```

## 📤 Add Images

### Manual:
Copy images to: `media/product_images/4B-BIO/` or `media/product_images/4B-ORANG/`

### Management Command:
```bash
# Interactive (prompts for each image)
python manage.py organize_product_images

# Auto-organize to specific database
python manage.py organize_product_images --database=4B-BIO

# Dry run (preview only)
python manage.py organize_product_images --dry-run
```

## 🔗 Image URLs
API returns both relative and full URLs:
```
product_image_url: /media/product_images/4B-BIO/FG00292-Gabru-Df.jpg
product_image_url_full: http://localhost:8000/media/product_images/4B-BIO/FG00292-Gabru-Df.jpg

product_description_urdu_url: /media/product_images/4B-BIO/FG00292-Gabru-DF-urdu.jpg
product_description_urdu_url_full: http://localhost:8000/media/product_images/4B-BIO/FG00292-Gabru-DF-urdu.jpg
```
The `_full` URLs include the configurable `BASE_URL` from settings.

## 📚 Full Documentation
See `PRODUCT_IMAGES_GUIDE.md` for complete details

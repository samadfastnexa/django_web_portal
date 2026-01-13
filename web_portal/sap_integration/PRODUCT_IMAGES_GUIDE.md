# Product Images Setup Guide

This document explains how product images are organized and accessed in the SAP Integration system.

## Folder Structure

Product images are stored in database-specific folders:

```
web_portal/media/product_images/
├── 4B-BIO/          # Images for 4B-BIO_APP database
│   ├── README.md
│   ├── FG00581.jpg
│   ├── FG00582.jpg
│   └── ...
└── 4B-ORANG/        # Images for 4B-ORANG_APP database
    ├── README.md
    ├── FG00581.jpg
    ├── FG00582.jpg
    └── ...
```

## Image Naming Convention

- Images must be named using the **filename from SAP** (stored in attachment tables)
- The filename format is usually: `{ItemCode}-{ProductName}.{extension}`
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`
- Examples from SAP:
  - `FG00292-Gabru-Df.jpg` (Product Image)
  - `FG00292-Gabru-DF-urdu.jpg` (Product Description Urdu)
  - `FG00581-Cotton-Seed.png`

**Important:** The image filenames come from SAP's attachment table (ATC1) and should match exactly.

## API Usage

### Products Catalog Endpoint

**Endpoint:** `GET /sap/products-catalog/`

**Query Parameters:**
- `database` (optional): Database name (e.g., `4B-BIO_APP` or `4B-ORANG_APP`)
  - If not provided, uses default from environment variables

**Example Requests:**

```bash
# Get products from 4B-BIO database
GET /sap/products-catalog/?database=4B-BIO_APP

# Get products from 4B-ORANG database
GET /sap/products-catalog/?database=4B-ORANG_APP

# Get products from default database
GET /sap/products-catalog/
```

**Response Format:**

```json
{
  "success": true,
  "count": 150,
  "database": "4B-BIO_APP",
  "data": [
    {
      "ItmsGrpCod": 106,
      "ItmsGrpNam": "Micronutrients",
      "Product_Catalog_Name": "Gabru-Df",
      "ItemCode": "FG00292",
      "ItemName": "Gabru-DF 80 WG-2KG",
      "U_GenericName": "Sulfur 80% DF",
      "U_BrandName": "Gabru-DF 80 WG2-Kgs.",
      "SalPackMsr": "2 KG",
      "Product_Image": "FG00292-Gabru-Df.jpg",
      "Product_Description_Urdu": "FG00292-Gabru-DF-urdu.jpg",
      "product_image_url": "/media/product_images/4B-BIO/FG00292-Gabru-Df.jpg",
      "product_description_urdu_url": "/media/product_images/4B-BIO/FG00292-Gabru-DF-urdu.jpg"
    }
  ]
}
```

## Adding New Product Images

### Method 1: Manual Upload

1. Navigate to `web_portal/media/product_images/`
2. Choose the appropriate database folder (`4B-BIO/` or `4B-ORANG/`)
3. Copy your image file with the **exact filename from SAP**
4. Example: Copy `FG00292-Gabru-Df.jpg` to `4B-BIO/` folder

**Important:** The filename must match exactly what SAP returns in the `Product_Image` field (e.g., `FG00292-Gabru-Df.jpg`)

### Method 2: Using Management Command

If you have images in a different location, use the Django management command to organize them:

```bash
# Interactive mode (prompts for each image)
python manage.py organize_product_images

# Specify source directory
python manage.py organize_product_images --source=/path/to/images

# Auto-organize all to specific database
python manage.py organize_product_images --database=4B-BIO

# Copy instead of move
python manage.py organize_product_images --copy

# Dry run (preview without making changes)
python manage.py organize_product_images --dry-run
```

**Command Options:**

- `--source`: Source directory containing images
- `--database`: Target database folder (4B-BIO or 4B-ORANG)
- `--copy`: Copy files instead of moving them
- `--dry-run`: Show what would be done without making changes

**Examples:**

```bash
# Move all images from temp folder to 4B-BIO
python manage.py organize_product_images --source=temp/images --database=4B-BIO

# Preview changes
python manage.py organize_product_images --dry-run

# Interactive organization
python manage.py organize_product_images
```

## Image URL Format

Images are accessible via the following URL pattern:

```
/media/product_images/{DATABASE_FOLDER}/{FILENAME_FROM_SAP}
```

**Examples:**
- `/media/product_images/4B-BIO/FG00292-Gabru-Df.jpg`
- `/media/product_images/4B-ORANG/FG00292-Gabru-Df.jpg`
- `/media/product_images/4B-BIO/FG00292-Gabru-DF-urdu.jpg`

The filenames come directly from SAP's attachment table.

## How It Works

1. **SAP Data Retrieval**: API fetches product data from SAP HANA, including:
   - `Product_Image`: Main product image filename (e.g., `FG00292-Gabru-Df.jpg`)
   - `Product_Description_Urdu`: Urdu description image filename (e.g., `FG00292-Gabru-DF-urdu.jpg`)

2. **Database Detection**: System extracts database name from the `database` parameter (e.g., `4B-BIO_APP` → `4B-BIO`)

3. **URL Generation**: For each product, the system generates two URL fields:
   - `product_image_url`: Full URL path to the product image
   - `product_description_urdu_url`: Full URL path to the Urdu description image

4. **File Matching**: URLs are constructed using the exact filenames from SAP, so the files in your folders must match exactly.

## Best Practices

1. **Exact Filename Matching**: Always use the exact filename from SAP's `Product_Image` field
2. **Database Separation**: Keep 4B-BIO and 4B-ORANG images separate
3. **Both Image Types**: Store both product images and Urdu description images
4. **Image Format**: Preserve the original format from SAP (jpg, png, etc.)
5. **File Size**: Optimize images before uploading (recommended: < 500KB per image)
6. **Backup**: Keep original images backed up before organizing

## Troubleshooting

### Image Not Showing

1. Check if file exists in correct folder
2. Verify filename matches SAP's `Product_Image` field **exactly**
3. Check file extension and capitalization
4. Ensure MEDIA_ROOT and MEDIA_URL are configured in settings.py

### Wrong Database Images

1. Verify `database` parameter in API request
2. Check if image exists in the correct database folder
3. Use management command to reorganize if needed

## Technical Notes

- **MEDIA_ROOT**: `BASE_DIR / 'media'`
- **MEDIA_URL**: `/media/`
- Image paths are relative to MEDIA_ROOT
- In production, serve media files through web server (nginx/apache)
- In development, Django serves media files automatically

"""
Test the image validator with a real PNG file
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from FieldAdvisoryService.validators import validate_image
from PIL import Image
import io

print("\n" + "="*60)
print("🧪 TESTING IMAGE VALIDATOR")
print("="*60 + "\n")

# Create a test PNG image
print("Creating test PNG image...")
img = Image.new('RGB', (100, 100), color='red')
img_bytes = io.BytesIO()
img.save(img_bytes, format='PNG')
img_bytes.seek(0)

# Create uploaded file
test_file = SimpleUploadedFile(
    name='test_image.png',
    content=img_bytes.read(),
    content_type='image/png'
)

print(f"Test file: {test_file.name}")
print(f"File size: {test_file.size} bytes")
print(f"Content type: {test_file.content_type}")

# Test validation
try:
    validate_image(test_file)
    print("\n✅ PNG image validation PASSED!")
except Exception as e:
    print(f"\n❌ PNG image validation FAILED: {e}")

# Test JPEG
print("\n" + "-"*60)
print("Creating test JPEG image...")
img_bytes.seek(0)
img2 = Image.new('RGB', (100, 100), color='blue')
img_bytes2 = io.BytesIO()
img2.save(img_bytes2, format='JPEG')
img_bytes2.seek(0)

test_file2 = SimpleUploadedFile(
    name='test_image.jpg',
    content=img_bytes2.read(),
    content_type='image/jpeg'
)

print(f"Test file: {test_file2.name}")
print(f"File size: {test_file2.size} bytes")
print(f"Content type: {test_file2.content_type}")

try:
    validate_image(test_file2)
    print("\n✅ JPEG image validation PASSED!")
except Exception as e:
    print(f"\n❌ JPEG image validation FAILED: {e}")

# Test invalid extension
print("\n" + "-"*60)
print("Testing invalid extension (BMP)...")
test_file3 = SimpleUploadedFile(
    name='test_image.bmp',
    content=img_bytes2.getvalue(),
    content_type='image/bmp'
)

try:
    validate_image(test_file3)
    print("\n❌ Should have rejected BMP file!")
except Exception as e:
    print(f"\n✅ Correctly rejected BMP: {e}")

print("\n" + "="*60)
print("✅ ALL TESTS COMPLETED")
print("="*60 + "\n")

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.core.validators import validate_email as django_validate_email
from PIL import Image
# CNIC must be 13 digits
cnic_validator = RegexValidator(
    r'^\d{5}-\d{7}-\d{1}$',
    message="CNIC must be in the format 12345-1234567-1"
)
# Phone number (international format)
phone_number_validator = RegexValidator(
    r'^\+?\d{10,15}$',
    message="Enter a valid international phone number."
)

def validate_latitude(value):
    if value < -90 or value > 90:
        raise ValidationError("Latitude must be between -90 and 90.")

def validate_longitude(value):
    if value < -180 or value > 180:
        raise ValidationError("Longitude must be between -180 and 180.")
def email_validator(value):
    if not value:
        raise ValidationError("Email cannot be empty.")

    try:
        django_validate_email(value)
    except ValidationError:
        raise ValidationError("Enter a valid email address.")

    if not value.endswith('.com'):  # Optional business rule
        raise ValidationError("Email must end with '.com'.")

    return value

def validate_image(image):
    # Check file type by content type if available
    if hasattr(image, 'file') and hasattr(image.file, 'content_type'):
        content_type = image.file.content_type
        if content_type not in ['image/jpeg', 'image/png']:
            raise ValidationError("Only JPEG and PNG images are allowed.")
    else:
        # Fallback: check based on extension or content (less reliable)
        try:
            img = Image.open(image)
            if img.format not in ['JPEG', 'PNG']:
                raise ValidationError("Uploaded file is not a valid image (JPEG or PNG).")
        except Exception:
            raise ValidationError("Uploaded file is not a valid image.")
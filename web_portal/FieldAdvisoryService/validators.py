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
    """
    Validate uploaded image format.
    Accepts JPEG and PNG formats only.
    Simple validation - just checks if PIL can open it.
    """
    if not image:
        return

    # Get the file name to check extension
    filename = getattr(image, 'name', '')
    if not filename:
        return

    # Check file extension
    allowed_extensions = ['jpg', 'jpeg', 'png']
    file_extension = filename.lower().split('.')[-1]
    
    if file_extension not in allowed_extensions:
        raise ValidationError(f"Only JPEG (.jpg, .jpeg) and PNG (.png) images are allowed. Your file: .{file_extension}")

    # Try to open with PIL to verify it's a valid image
    try:
        # Reset file pointer to beginning if possible
        if hasattr(image, 'seek'):
            try:
                image.seek(0)
            except:
                pass
        
        # Try to open the image
        img = Image.open(image)
        # Just load to verify it's valid
        img.load()
            
    except FileNotFoundError:
        # File doesn't exist yet, skip validation
        return
    except (IOError, OSError) as e:
        # Not a valid image file
        raise ValidationError(f"The uploaded file is not a valid image: {str(e)}")
    except Exception as e:
        # For any other PIL errors
        raise ValidationError(f"Could not validate image file: {str(e)}")
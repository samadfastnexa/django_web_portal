"""
JazzCash Payment Gateway Configuration

Add these settings to your Django settings.py file or environment variables.
"""

# ==============================================================================
# JAZZCASH PAYMENT GATEWAY SETTINGS
# ==============================================================================

# JazzCash Merchant Credentials
# Get these from your JazzCash merchant account
JAZZCASH_MERCHANT_ID = 'MC12345'  # Replace with your merchant ID
JAZZCASH_PASSWORD = 'your_password'  # Replace with your password
JAZZCASH_INTEGRITY_SALT = 'your_integrity_salt'  # Replace with your salt

# Environment Configuration
JAZZCASH_USE_SANDBOX = True  # Set to False in production

# Site Configuration
# This is used for payment callback URLs
SITE_URL = 'http://localhost:8000'  # Update for production (e.g., 'https://yourdomain.com')

# ==============================================================================
# CART SETTINGS
# ==============================================================================

# Cart item expiry time (in hours)
# Cart items will be automatically marked inactive after this duration
CART_EXPIRY_HOURS = 24

# ==============================================================================
# ENVIRONMENT VARIABLES (.env file)
# ==============================================================================
# 
# For production, use environment variables instead of hardcoding credentials:
#
# JAZZCASH_MERCHANT_ID=your_merchant_id
# JAZZCASH_PASSWORD=your_password
# JAZZCASH_INTEGRITY_SALT=your_integrity_salt
# JAZZCASH_USE_SANDBOX=False
# SITE_URL=https://yourdomain.com
#
# Then in settings.py use:
# import os
# from pathlib import Path
# 
# JAZZCASH_MERCHANT_ID = os.getenv('JAZZCASH_MERCHANT_ID', 'MC12345')
# JAZZCASH_PASSWORD = os.getenv('JAZZCASH_PASSWORD', 'test_password')
# JAZZCASH_INTEGRITY_SALT = os.getenv('JAZZCASH_INTEGRITY_SALT', 'test_salt')
# JAZZCASH_USE_SANDBOX = os.getenv('JAZZCASH_USE_SANDBOX', 'True') == 'True'
# SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')
#
# ==============================================================================

# ==============================================================================
# LOGGING CONFIGURATION (Optional but recommended)
# ==============================================================================
# 
# Add payment gateway logging to LOGGING configuration in settings.py:
#
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'payment_file': {
#             'level': 'INFO',
#             'class': 'logging.FileHandler',
#             'filename': 'logs/payments.log',
#         },
#     },
#     'loggers': {
#         'cart.jazzcash_service': {
#             'handlers': ['payment_file'],
#             'level': 'INFO',
#             'propagate': False,
#         },
#         'cart.views': {
#             'handlers': ['payment_file'],
#             'level': 'INFO',
#             'propagate': False,
#         },
#     },
# }
#
# ==============================================================================

# ==============================================================================
# CELERY CONFIGURATION (Optional - for automated cart cleanup)
# ==============================================================================
#
# If using Celery for background tasks, add this to your celery.py:
#
# from celery import shared_task
# from celery.schedules import crontab
#
# @shared_task
# def clean_expired_carts():
#     from django.core.management import call_command
#     call_command('clean_expired_carts')
#
# # In celery beat schedule:
# CELERY_BEAT_SCHEDULE = {
#     'clean-expired-carts': {
#         'task': 'yourapp.tasks.clean_expired_carts',
#         'schedule': crontab(hour='*/1'),  # Run every hour
#     },
# }
#
# ==============================================================================

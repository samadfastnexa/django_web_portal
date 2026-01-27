"""
JazzCash Payment Gateway Integration Service

This module provides integration with JazzCash's Mobile Account API
for processing payments in Pakistan.

Documentation: https://sandbox.jazzcash.com.pk/
"""

import hashlib
import hmac
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class JazzCashConfig:
    """JazzCash configuration from Django settings"""
    
    # Get from settings or use defaults for testing
    MERCHANT_ID = getattr(settings, 'JAZZCASH_MERCHANT_ID', 'MC12345')
    PASSWORD = getattr(settings, 'JAZZCASH_PASSWORD', 'test_password')
    INTEGRITY_SALT = getattr(settings, 'JAZZCASH_INTEGRITY_SALT', 'test_salt')
    
    # API URLs
    SANDBOX_URL = 'https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform'
    PRODUCTION_URL = 'https://payments.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform'
    
    # Use sandbox by default
    USE_SANDBOX = getattr(settings, 'JAZZCASH_USE_SANDBOX', True)
    
    @classmethod
    def get_api_url(cls):
        """Get appropriate API URL based on environment"""
        return cls.SANDBOX_URL if cls.USE_SANDBOX else cls.PRODUCTION_URL
    
    @classmethod
    def get_return_url(cls):
        """Get payment return URL"""
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{base_url}/api/cart/payments/jazzcash/return/"
    
    @classmethod
    def get_post_url(cls):
        """Get payment POST/callback URL"""
        base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        return f"{base_url}/api/cart/payments/jazzcash/callback/"


class JazzCashService:
    """
    Service class for JazzCash payment integration.
    
    Handles:
    - Payment request generation
    - Secure hash calculation
    - Payment verification
    - Callback processing
    """
    
    def __init__(self):
        self.config = JazzCashConfig()
    
    def generate_secure_hash(self, data_dict):
        """
        Generate HMAC-SHA256 secure hash for JazzCash API
        
        Args:
            data_dict: Dictionary containing payment parameters
            
        Returns:
            str: Secure hash string
        """
        # Sort keys alphabetically (JazzCash requirement)
        sorted_string = '&'.join(
            f"{key}={value}" 
            for key, value in sorted(data_dict.items())
        )
        
        # Add integrity salt
        sorted_string = self.config.INTEGRITY_SALT + '&' + sorted_string
        
        # Generate HMAC-SHA256 hash
        secure_hash = hmac.new(
            self.config.INTEGRITY_SALT.encode('utf-8'),
            sorted_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return secure_hash.upper()
    
    def create_payment_request(self, order, amount, customer_mobile, customer_email=None):
        """
        Create JazzCash payment request
        
        Args:
            order: Order instance
            amount: Payment amount (Decimal)
            customer_mobile: Customer mobile number (format: 03xxxxxxxxx)
            customer_email: Customer email (optional)
            
        Returns:
            dict: Payment request data including form fields and URL
        """
        # Generate unique transaction reference
        transaction_ref = f"T{timezone.now().strftime('%Y%m%d%H%M%S')}{order.id}"
        
        # Current timestamp
        current_time = datetime.now()
        
        # Convert amount to paisa (JazzCash uses smallest currency unit)
        amount_in_paisa = int(amount * 100)
        
        # Prepare payment data
        payment_data = {
            'pp_Version': '1.1',
            'pp_TxnType': 'MWALLET',  # Mobile Wallet transaction
            'pp_Language': 'EN',
            'pp_MerchantID': self.config.MERCHANT_ID,
            'pp_SubMerchantID': '',
            'pp_Password': self.config.PASSWORD,
            'pp_BankID': '',
            'pp_ProductID': '',
            'pp_TxnRefNo': transaction_ref,
            'pp_Amount': str(amount_in_paisa),
            'pp_TxnCurrency': 'PKR',
            'pp_TxnDateTime': current_time.strftime('%Y%m%d%H%M%S'),
            'pp_BillReference': order.order_number,
            'pp_Description': f'Payment for Order {order.order_number}',
            'pp_TxnExpiryDateTime': (current_time + timedelta(hours=1)).strftime('%Y%m%d%H%M%S'),
            'pp_ReturnURL': self.config.get_return_url(),
            'pp_SecureHash': '',  # Will be calculated
            'ppmpf_1': '',  # Optional fields
            'ppmpf_2': '',
            'ppmpf_3': '',
            'ppmpf_4': '',
            'ppmpf_5': '',
        }
        
        # Add customer information if provided
        if customer_mobile:
            payment_data['pp_MobileNumber'] = customer_mobile
        if customer_email:
            payment_data['pp_CustomerEmail'] = customer_email
        
        # Calculate secure hash (exclude pp_SecureHash itself)
        hash_data = {k: v for k, v in payment_data.items() if k != 'pp_SecureHash' and v != ''}
        payment_data['pp_SecureHash'] = self.generate_secure_hash(hash_data)
        
        return {
            'api_url': self.config.get_api_url(),
            'transaction_ref': transaction_ref,
            'payment_data': payment_data,
            'amount': amount,
            'amount_in_paisa': amount_in_paisa,
        }
    
    def verify_payment_response(self, response_data):
        """
        Verify JazzCash payment response
        
        Args:
            response_data: Dictionary containing JazzCash response parameters
            
        Returns:
            dict: Verification result with status and details
        """
        try:
            # Extract secure hash from response
            received_hash = response_data.get('pp_SecureHash', '')
            
            # Prepare data for hash calculation (exclude hash itself)
            hash_data = {
                k: v for k, v in response_data.items() 
                if k != 'pp_SecureHash' and v is not None and v != ''
            }
            
            # Calculate expected hash
            expected_hash = self.generate_secure_hash(hash_data)
            
            # Verify hash
            if received_hash != expected_hash:
                logger.warning(f"JazzCash hash mismatch. Expected: {expected_hash}, Received: {received_hash}")
                return {
                    'success': False,
                    'error': 'Invalid secure hash',
                    'response_code': response_data.get('pp_ResponseCode'),
                    'response_message': response_data.get('pp_ResponseMessage'),
                }
            
            # Check response code (000 = success)
            response_code = response_data.get('pp_ResponseCode', '')
            
            return {
                'success': response_code == '000',
                'response_code': response_code,
                'response_message': response_data.get('pp_ResponseMessage', ''),
                'transaction_ref': response_data.get('pp_TxnRefNo', ''),
                'jazzcash_transaction_id': response_data.get('pp_TxnRefNo', ''),
                'amount': Decimal(response_data.get('pp_Amount', 0)) / 100,  # Convert from paisa
                'bill_reference': response_data.get('pp_BillReference', ''),
                'raw_response': response_data,
            }
            
        except Exception as e:
            logger.error(f"Error verifying JazzCash payment: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'raw_response': response_data,
            }
    
    def get_transaction_status(self, transaction_ref):
        """
        Query JazzCash for transaction status
        
        Args:
            transaction_ref: Transaction reference number
            
        Returns:
            dict: Transaction status information
        """
        # JazzCash transaction inquiry endpoint
        inquiry_url = 'https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform'
        
        # Prepare inquiry data
        current_time = datetime.now()
        inquiry_data = {
            'pp_Version': '1.1',
            'pp_TxnType': 'INQUIRY',
            'pp_Language': 'EN',
            'pp_MerchantID': self.config.MERCHANT_ID,
            'pp_Password': self.config.PASSWORD,
            'pp_TxnRefNo': transaction_ref,
            'pp_TxnDateTime': current_time.strftime('%Y%m%d%H%M%S'),
        }
        
        # Calculate secure hash
        inquiry_data['pp_SecureHash'] = self.generate_secure_hash(
            {k: v for k, v in inquiry_data.items() if k != 'pp_SecureHash'}
        )
        
        try:
            # Make API request
            response = requests.post(inquiry_url, data=inquiry_data, timeout=30)
            response.raise_for_status()
            
            # Parse response
            result = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            
            return {
                'success': True,
                'data': result,
            }
            
        except requests.RequestException as e:
            logger.error(f"Error querying JazzCash transaction status: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }


# Response code mappings for better user feedback
JAZZCASH_RESPONSE_CODES = {
    '000': 'Transaction Successful',
    '001': 'Transaction Declined',
    '002': 'Transaction Cancelled',
    '121': 'Invalid Merchant ID',
    '124': 'Invalid Transaction Amount',
    '157': 'Transaction Expired',
    '158': 'Insufficient Balance',
    '200': 'Invalid Credentials',
    '947': 'Transaction Already Processed',
}


def get_jazzcash_response_message(code):
    """Get human-readable message for JazzCash response code"""
    return JAZZCASH_RESPONSE_CODES.get(code, f'Unknown response code: {code}')

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import re

User = get_user_model()


class EmailOrPhoneBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with:
    - Email address (all user types)
    - Phone number (Farmers, Sales Staff, Dealers)
    
    Phone Number Sources:
    - Farmers: User.username (phone stored as username)
    - Sales Staff: SalesStaffProfile.phone_number
    - Dealers: Dealer.contact_number OR Dealer.mobile_phone
    
    Phone Number Normalization:
    - All formats accepted: 0300-123-4567, 03001234567, 0300 123 4567, (0300) 123-4567
    - Normalized to digits only for matching
    
    Usage:
        In settings.py, add:
        AUTHENTICATION_BACKENDS = [
            'accounts.backends.EmailOrPhoneBackend',
            'django.contrib.auth.backends.ModelBackend',
        ]
    """
    
    @staticmethod
    def normalize_phone(phone_number):
        """
        Normalize phone number by keeping only digits and handling country codes.
        
        Examples:
            0300-123-4567 → 03001234567
            0300 123 4567 → 03001234567
            (0300) 123-4567 → 03001234567
            923001234567 → 03001234567 (removes +92 country code)
            +923001234567 → 03001234567 (removes +92 country code)
        """
        if not phone_number:
            return ''
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone_number)
        
        # Handle Pakistani country code (+92)
        # If starts with 92 and has 12 digits total (92 + 10 digits), remove 92 and add 0
        if digits_only.startswith('92') and len(digits_only) == 12:
            return '0' + digits_only[2:]
        
        return digits_only
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user by email or phone number.
        
        Args:
            username: Can be email, username (farmer phone), or phone number
            password: User's password
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        if username is None or password is None:
            return None
        
        # Normalize the input (strip whitespace)
        username = username.strip()
        
        user = None
        
        try:
            # Try to find user by email or username (farmers use phone as username)
            user = User.objects.get(
                Q(email__iexact=username) | 
                Q(username=username)
            )
        except User.DoesNotExist:
            # If not found, try phone number lookup in profiles
            user = self._find_user_by_phone(username)
        except User.MultipleObjectsReturned:
            # Multiple users found, return None for security
            return None
        
        # Check the password
        if user and user.check_password(password):
            return user
        
        return None
    
    def _find_user_by_phone(self, phone_number):
        """
        Find user by phone number from different profile types.
        Normalizes phone numbers to digits-only for flexible matching.
        
        Args:
            phone_number: Phone number to search (any format)
            
        Returns:
            User object if found, None otherwise
        """
        # Normalize the input phone number (remove all non-digits)
        normalized_input = self.normalize_phone(phone_number)
        
        if not normalized_input:
            return None
        
        # Try Sales Staff Profile
        try:
            from .models import SalesStaffProfile
            # Get all profiles and check normalized phone numbers
            for profile in SalesStaffProfile.objects.select_related('user').all():
                if self.normalize_phone(profile.phone_number) == normalized_input:
                    return profile.user
        except Exception:
            pass
        
        # Try Dealer (contact_number)
        try:
            from FieldAdvisoryService.models import Dealer
            for dealer in Dealer.objects.select_related('user').filter(user__isnull=False):
                if self.normalize_phone(dealer.contact_number) == normalized_input:
                    return dealer.user
        except Exception:
            pass
        
        # Try Dealer (mobile_phone)
        try:
            from FieldAdvisoryService.models import Dealer
            for dealer in Dealer.objects.select_related('user').filter(user__isnull=False):
                if dealer.mobile_phone and self.normalize_phone(dealer.mobile_phone) == normalized_input:
                    return dealer.user
        except Exception:
            pass
        
        # Try User.username (for farmers who use phone as username)
        try:
            for user in User.objects.all():
                if self.normalize_phone(user.username) == normalized_input:
                    return user
        except Exception:
            pass
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID.
        Required by Django's authentication system.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

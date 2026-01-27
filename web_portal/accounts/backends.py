from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

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
    
    Usage:
        In settings.py, add:
        AUTHENTICATION_BACKENDS = [
            'accounts.backends.EmailOrPhoneBackend',
            'django.contrib.auth.backends.ModelBackend',
        ]
    """
    
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
        
        Args:
            phone_number: Phone number to search
            
        Returns:
            User object if found, None otherwise
        """
        # Try Sales Staff Profile
        try:
            from .models import SalesStaffProfile
            profile = SalesStaffProfile.objects.select_related('user').get(
                phone_number=phone_number
            )
            return profile.user
        except:
            pass
        
        # Try Dealer (contact_number)
        try:
            from FieldAdvisoryService.models import Dealer
            dealer = Dealer.objects.select_related('user').get(
                contact_number=phone_number
            )
            if dealer.user:
                return dealer.user
        except:
            pass
        
        # Try Dealer (mobile_phone)
        try:
            from FieldAdvisoryService.models import Dealer
            dealer = Dealer.objects.select_related('user').get(
                mobile_phone=phone_number
            )
            if dealer.user:
                return dealer.user
        except:
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

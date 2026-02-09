from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers

User = get_user_model()


class MyTokenObtainPairSerializer(serializers.Serializer):
    """
    JWT Token Authentication Serializer
    
    Supports authentication for all user types:
    1. Login with Email: Provide 'email' and 'password'
    2. Login with Phone Number: Provide 'phone_number' and 'password'
    
    Phone Number Sources by User Type:
    - Farmers: Phone stored in User.username
    - Sales Staff: Phone from SalesStaffProfile.phone_number
    - Dealers: Phone from Dealer.contact_number or mobile_phone
    
    Examples:
    - Email login: {"email": "user@example.com", "password": "your_password"}
    - Phone login (any type): {"phone_number": "03001234567", "password": "your_password"}
    """
    # Accept either email or phone_number for login
    email = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="User's email address (optional if phone_number is provided)"
    )
    phone_number = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="User's phone number (optional if email is provided) - works for all user types"
    )
    password = serializers.CharField(
        write_only=True,
        help_text="User's password"
    )

    # -----------------------------------------------------------
    # 1.  Turn built-in field errors into a single string
    # -----------------------------------------------------------
    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError as exc:
            # exc.detail is a dict like {'email': ['Bad email.']}
            first_key, first_msgs = next(iter(exc.detail.items()))
            text = str(first_msgs[0]) if isinstance(first_msgs, list) else str(first_msgs)
            raise serializers.ValidationError({"message": text})

    # -----------------------------------------------------------
    # 2.  All custom checks → single string under "message"
    # -----------------------------------------------------------
    def validate(self, attrs):
        # Normalize inputs
        raw_email = attrs.get("email", "").strip()
        raw_phone = attrs.get("phone_number", "").strip()
        password = attrs.get("password")

        # Must provide either email or phone_number
        if not raw_email and not raw_phone:
            raise serializers.ValidationError({"message": "Email or phone number is required."})
        
        if not password:
            raise serializers.ValidationError({"message": "Password is required."})

        # Smart detection: if email field contains only digits/+/-, treat as phone
        username = raw_email if raw_email else raw_phone
        
        # If username looks like a phone number (only digits, +, -, spaces), treat as phone
        # This allows users to enter phone in email field
        if username and username.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            # It's a phone number, use it directly
            credential_type = 'phone'
        elif '@' in username:
            # It's an email
            credential_type = 'email'
        else:
            # Could be username (for farmers) or phone, try as is
            credential_type = 'username'

        # Use Django's authenticate function (which will use our custom backend)
        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError({"message": "Invalid email/phone number or password."})

        if not user.is_active:
            raise serializers.ValidationError({"message": "User account is inactive."})

        # --- build successful response ---
        refresh = RefreshToken.for_user(user)

        role = getattr(user, "role", None)
        role_name = role.name if role else None

        permissions = list(role.permissions.values("id", "codename")) if role else []

        companies_data, default_company_data = [], None
        
        # Check for Sales Staff Profile
        profile = getattr(user, "sales_profile", None)
        if profile:
            companies_qs = profile.companies.all()
            for i, c in enumerate(companies_qs):
                companies_data.append({
                    "id": c.id,
                    "name": c.Company_name,
                    "default": i == 0,
                })
                if i == 0:
                    default_company_data = {"id": c.id, "name": c.Company_name}
        
        # Check for Dealer Profile
        else:
            try:
                from FieldAdvisoryService.models import Dealer
                dealer = Dealer.objects.filter(user=user).first()
                if dealer and dealer.company:
                    companies_data.append({
                        "id": dealer.company.id,
                        "name": dealer.company.Company_name,
                        "default": True,
                    })
                    default_company_data = {"id": dealer.company.id, "name": dealer.company.Company_name}
            except Exception:
                pass

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "companies": companies_data,
            "default_company": default_company_data,
            "email": user.email,
            "username": user.username,
            "role": role_name,
            "permissions": permissions,
        }
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model 
from rest_framework import serializers

User = get_user_model()
class MyTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('No user found with this email address.')

        if not user.check_password(password):
            raise serializers.ValidationError('Incorrect password.')

        if not user.is_active:
            raise serializers.ValidationError('User account is inactive.')

        # ✅ Generate JWT tokens manually
        refresh = RefreshToken.for_user(user)

        # ✅ Get role name
        role = getattr(user, 'role', None)
        role_name = role.name if role else None

        # ✅ Get permissions (id + codename)
        permissions = []
        if role:
            permissions = list(role.permissions.values('id', 'codename'))

        # ✅ Get companies from sales_profile
        companies_data = []
        profile = getattr(user, "sales_profile", None)
        if profile:
            companies_qs = profile.companies.all()
            for i, c in enumerate(companies_qs):
                company_dict = {
                    "id": c.id,
                    "name": c.Company_name,
                    "default": i == 0
                }
                companies_data.append(company_dict)
                if i == 0:
                    default_company_data = {"id": c.id, "name": c.Company_name}

        return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user_id": user.id,
        "companies": companies_data,
        "default_company": default_company_data,  # 👈 add this
        "email": user.email,
        "username": user.username,
        "role": role_name,
        "permissions": permissions,
    }
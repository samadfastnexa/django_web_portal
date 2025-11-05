from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class MyTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

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
        raw_email = attrs.get("email")
        password = attrs.get("password")
        email = (raw_email or "").strip()

        if not email:
            raise serializers.ValidationError({"message": "Email is required."})
        if not password:
            raise serializers.ValidationError({"message": "Password is required."})

        # Case-insensitive lookup and uniform error to avoid account enumeration
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"message": "Invalid email or password."})

        if not user.check_password(password):
            raise serializers.ValidationError({"message": "Invalid email or password."})

        if not user.is_active:
            raise serializers.ValidationError({"message": "User account is inactive."})

        # --- build successful response ---
        refresh = RefreshToken.for_user(user)

        role = getattr(user, "role", None)
        role_name = role.name if role else None

        permissions = list(role.permissions.values("id", "codename")) if role else []

        companies_data, default_company_data = [], None
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
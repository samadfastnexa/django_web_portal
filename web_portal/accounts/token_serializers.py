# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth import get_user_model 
# from rest_framework import serializers

# User = get_user_model()
# class MyTokenObtainPairSerializer(serializers.Serializer):
#     email = serializers.EmailField()
#     password = serializers.CharField(write_only=True)
    
#     def validate(self, attrs):
#         email = attrs.get('email')
#         password = attrs.get('password')

#         if not email or not password:
#             raise serializers.ValidationError('Email and password are required.')

#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             raise serializers.ValidationError('No user found with this email address.')

#         if not user.check_password(password):
#             raise serializers.ValidationError('Incorrect password.')

#         if not user.is_active:
#             raise serializers.ValidationError('User account is inactive.')

#         # ✅ Generate JWT tokens manually
#         refresh = RefreshToken.for_user(user)

#         # ✅ Get role name
#         role = getattr(user, 'role', None)
#         role_name = role.name if role else None

#         # ✅ Get permissions (id + codename)
#         permissions = []
#         if role:
#             permissions = list(role.permissions.values('id', 'codename'))

#         # ✅ Get companies from sales_profile
#         companies_data = []
#         profile = getattr(user, "sales_profile", None)
#         if profile:
#             companies_qs = profile.companies.all()
#             for i, c in enumerate(companies_qs):
#                 company_dict = {
#                     "id": c.id,
#                     "name": c.Company_name,
#                     "default": i == 0
#                 }
#                 companies_data.append(company_dict)
#                 if i == 0:
#                     default_company_data = {"id": c.id, "name": c.Company_name}

#         return {
#         "refresh": str(refresh),
#         "access": str(refresh.access_token),
#         "user_id": user.id,
#         "companies": companies_data,
#         "default_company": default_company_data,  # 👈 add this
#         "email": user.email,
#         "username": user.username,
#         "role": role_name,
#         "permissions": permissions,
#     }



# from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth import get_user_model
# from rest_framework import serializers

# User = get_user_model()

# class MyTokenObtainPairSerializer(serializers.Serializer):
#     email = serializers.EmailField()
#     password = serializers.CharField(write_only=True)

#     def to_internal_value(self, data):
#         """Override field error messages to return {'message': '...'} instead of {'field': [...]}"""
#         try:
#             return super().to_internal_value(data)
#         except serializers.ValidationError as e:
#             error_dict = e.detail
#             if isinstance(error_dict, dict):
#                 first_field, messages = next(iter(error_dict.items()))
#                 if isinstance(messages, list) and messages:
#                     raise serializers.ValidationError({"message": str(messages[0])})
#                 else:
#                     raise serializers.ValidationError({"message": str(messages)})
#             raise e

#     def validate(self, attrs):
#         email = attrs.get("email")
#         password = attrs.get("password")

#         if not email:
#             raise serializers.ValidationError({"message": "Email is required."})

#         if not password:
#             raise serializers.ValidationError({"message": "Password is required."})

#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             raise serializers.ValidationError({"message": "No user found with this email address."})

#         if not user.check_password(password):
#             raise serializers.ValidationError({"message": "Incorrect password."})

#         if not user.is_active:
#             raise serializers.ValidationError({"message": "User account is inactive."})

#         # ✅ Generate JWT tokens manually
#         refresh = RefreshToken.for_user(user)

#         # ✅ Get role name
#         role = getattr(user, "role", None)
#         role_name = role.name if role else None

#         # ✅ Get permissions (id + codename)
#         permissions = []
#         if role:
#             permissions = list(role.permissions.values("id", "codename"))

#         # ✅ Get companies from sales_profile
#         companies_data = []
#         default_company_data = None
#         profile = getattr(user, "sales_profile", None)
#         if profile:
#             companies_qs = profile.companies.all()
#             for i, c in enumerate(companies_qs):
#                 company_dict = {
#                     "id": c.id,
#                     "name": c.Company_name,
#                     "default": i == 0,
#                 }
#                 companies_data.append(company_dict)
#                 if i == 0:
#                     default_company_data = {"id": c.id, "name": c.Company_name}

#         return {
#             "refresh": str(refresh),
#             "access": str(refresh.access_token),
#             "user_id": user.id,
#             "companies": companies_data,
#             "default_company": default_company_data,
#             "email": user.email,
#             "username": user.username,
#             "role": role_name,
#             "permissions": permissions,
#         }


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
        email = attrs.get("email")
        password = attrs.get("password")

        if not email:
            raise serializers.ValidationError({"message": "Email is required."})
        if not password:
            raise serializers.ValidationError({"message": "Password is required."})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"message": "No user found with this email address."})

        if not user.check_password(password):
            raise serializers.ValidationError({"message": "Incorrect password."})

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
# django_wed_panel/web_portal/accounts/filters.py

import django_filters
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFilter(django_filters.FilterSet):
    # Basic user fields
    email = django_filters.CharFilter(field_name='email', lookup_expr='icontains')
    username = django_filters.CharFilter(field_name='username', lookup_expr='icontains')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    role = django_filters.NumberFilter(field_name='role__id')

    # 🔑 Sales profile related fields
    company = django_filters.NumberFilter(field_name="sales_profile__companies__id")
    region = django_filters.NumberFilter(field_name="sales_profile__regions__id")
    zone = django_filters.NumberFilter(field_name="sales_profile__zones__id")
    territory = django_filters.NumberFilter(field_name="sales_profile__territories__id")

    designation = django_filters.CharFilter(field_name="sales_profile__designation", lookup_expr="icontains")
    employee_code = django_filters.CharFilter(field_name="sales_profile__employee_code", lookup_expr="icontains")

    class Meta:
        model = User
        fields = [
            'email', 'username', 'is_active', 'role',
            'company', 'region', 'zone', 'territory',
            'designation', 'employee_code'
        ]

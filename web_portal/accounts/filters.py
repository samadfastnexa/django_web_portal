import django_filters
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(field_name='email', lookup_expr='icontains')
    username = django_filters.CharFilter(field_name='username', lookup_expr='icontains')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    role = django_filters.NumberFilter(field_name='role__id')

    class Meta:
        model = User
        fields = ['email', 'username', 'is_active', 'role']
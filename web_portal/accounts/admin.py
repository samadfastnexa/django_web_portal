from django.contrib import admin
from .models import User, Role

admin.site.register(User)
# admin.site.register(Product)
# admin.site.register(Order)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    filter_horizontal = ['permissions']  # To show a multi-select UI for permissions
from django.contrib import admin
from .models import Complaint

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['complaint_id', 'user', 'status', 'created_at']
    search_fields = ['complaint_id', 'user__username', 'message']
    list_filter = ['status', 'created_at']
    readonly_fields = ['status']  # ✅ Makes status uneditable

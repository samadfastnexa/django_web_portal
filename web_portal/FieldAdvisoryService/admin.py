from django.contrib import admin
from .models import Dealer, MeetingSchedule, SalesOrder, SalesOrderAttachment

admin.site.register(Dealer)
admin.site.register(MeetingSchedule)
admin.site.register(SalesOrder)
admin.site.register(SalesOrderAttachment)

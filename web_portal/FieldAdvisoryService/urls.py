from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import DealerViewSet, MeetingScheduleViewSet, SalesOrderViewSet

router = DefaultRouter()
router.register(r'dealers', DealerViewSet)
router.register(r'schedule', MeetingScheduleViewSet)
router.register(r'sales-orders', SalesOrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

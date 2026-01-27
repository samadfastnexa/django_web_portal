from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CartViewSet,
    OrderViewSet,
    PaymentViewSet,
    JazzCashCallbackView,
    JazzCashReturnView,
)

router = DefaultRouter()
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    # JazzCash payment gateway endpoints
    path('payments/jazzcash/callback/', JazzCashCallbackView.as_view(), name='jazzcash-callback'),
    path('payments/jazzcash/return/', JazzCashReturnView.as_view(), name='jazzcash-return'),
]

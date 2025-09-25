from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CropViewSet, CropStageViewSet

router = DefaultRouter()
router.register(r'crops', CropViewSet, basename='crops')
router.register(r'stages', CropStageViewSet, basename='stages')

urlpatterns = [
    path('', include(router.urls)),
]

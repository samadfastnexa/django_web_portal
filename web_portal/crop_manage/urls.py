from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CropViewSet, CropStageViewSet, station_trials

router = DefaultRouter()
router.register(r'crops', CropViewSet, basename='crops')
router.register(r'stages', CropStageViewSet, basename='stages')

urlpatterns = [
    path('', include(router.urls)),
    path('trials/<str:station_slug>/', station_trials, name='station_trials'),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CropViewSet, CropStageViewSet, station_trials, export_trials_xlsx, export_trials_pdf

router = DefaultRouter()
router.register(r'crops', CropViewSet, basename='crops')
router.register(r'stages', CropStageViewSet, basename='stages')

urlpatterns = [
    path('', include(router.urls)),
    path('trials/<str:station_slug>/', station_trials, name='station_trials'),
    path('trials/export/xlsx/', export_trials_xlsx, name='export_trials_xlsx'),
    path('trials/export/pdf/', export_trials_pdf, name='export_trials_pdf'),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'crops', views.CropViewSet, basename='crop')
router.register(r'varieties', views.CropVarietyViewSet, basename='cropvariety')
router.register(r'yield-data', views.YieldDataViewSet, basename='yielddata')
router.register(r'farming-practices', views.FarmingPracticeViewSet, basename='farmingpractice')
router.register(r'research', views.CropResearchViewSet, basename='cropresearch')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('api/', include(router.urls)),
    
    # Additional custom endpoints
    path('api/crops/<int:crop_id>/varieties/', 
         views.CropViewSet.as_view({'get': 'varieties'}), 
         name='crop-varieties'),
    
    path('api/crops/<int:crop_id>/yield-summary/', 
         views.CropViewSet.as_view({'get': 'yield_summary'}), 
         name='crop-yield-summary'),
    
    path('api/crops/<int:crop_id>/analytics/', 
         views.CropViewSet.as_view({'get': 'analytics'}), 
         name='crop-analytics'),
    
    path('api/varieties/<int:variety_id>/yield-data/', 
         views.CropVarietyViewSet.as_view({'get': 'yield_data'}), 
         name='variety-yield-data'),
    
    path('api/yield-data/summary/', 
         views.YieldDataViewSet.as_view({'get': 'summary'}), 
         name='yield-summary'),
    
    path('api/yield-data/analytics/', 
         views.YieldDataViewSet.as_view({'get': 'analytics'}), 
         name='yield-analytics'),
    
    path('api/yield-data/trends/', 
         views.YieldDataViewSet.as_view({'get': 'trends'}), 
         name='yield-trends'),
    
    path('api/farming-practices/by-crop/<int:crop_id>/', 
         views.FarmingPracticeViewSet.as_view({'get': 'by_crop'}), 
         name='practices-by-crop'),
    
    path('api/farming-practices/recommended/', 
         views.FarmingPracticeViewSet.as_view({'get': 'recommended'}), 
         name='recommended-practices'),
    
    path('api/research/by-crop/<int:crop_id>/', 
         views.CropResearchViewSet.as_view({'get': 'by_crop'}), 
         name='research-by-crop'),
    
    path('api/research/recent/', 
         views.CropResearchViewSet.as_view({'get': 'recent'}), 
         name='recent-research'),
    
    path('api/research/published/', 
         views.CropResearchViewSet.as_view({'get': 'published'}), 
         name='published-research'),
]

# Add app name for namespacing
app_name = 'crop_management'
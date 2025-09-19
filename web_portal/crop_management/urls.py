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
    path('', include(router.urls)),
    
    # Additional custom endpoints
    path('crops/<int:crop_id>/varieties/', 
         views.CropViewSet.as_view({'get': 'varieties'}), 
         name='crop-varieties'),
    
    path('crops/<int:crop_id>/yield-summary/', 
         views.CropViewSet.as_view({'get': 'yield_summary'}), 
         name='crop-yield-summary'),
    
    path('crops/<int:crop_id>/analytics/', 
         views.CropViewSet.as_view({'get': 'analytics'}), 
         name='crop-analytics'),
    
    path('varieties/<int:variety_id>/yield-data/', 
         views.CropVarietyViewSet.as_view({'get': 'yield_data'}), 
         name='variety-yield-data'),
    
    path('yield-data/summary/', 
         views.YieldDataViewSet.as_view({'get': 'summary'}), 
         name='yield-summary'),
    
    path('yield-data/analytics/', 
         views.YieldDataViewSet.as_view({'get': 'analytics'}), 
         name='yield-analytics'),
    
    path('yield-data/trends/', 
         views.YieldDataViewSet.as_view({'get': 'trends'}), 
         name='yield-trends'),
    
    path('farming-practices/by-crop/<int:crop_id>/', 
         views.FarmingPracticeViewSet.as_view({'get': 'by_crop'}), 
         name='practices-by-crop'),
    
    path('farming-practices/recommended/', 
         views.FarmingPracticeViewSet.as_view({'get': 'recommended'}), 
         name='recommended-practices'),
    
    path('research/by-crop/<int:crop_id>/', 
         views.CropResearchViewSet.as_view({'get': 'by_crop'}), 
         name='research-by-crop'),
    
    path('research/recent/', 
         views.CropResearchViewSet.as_view({'get': 'recent'}), 
         name='recent-research'),
    
    path('research/published/', 
         views.CropResearchViewSet.as_view({'get': 'published'}), 
         name='published-research'),
]

# Add app name for namespacing
app_name = 'crop_management'
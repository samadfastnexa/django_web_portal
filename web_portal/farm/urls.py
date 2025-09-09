# farm/urls.py
from rest_framework.routers import DefaultRouter
from .views import FarmViewSet

router = DefaultRouter()
router.register(r'farms', FarmViewSet, basename='farm')

urlpatterns = router.urls

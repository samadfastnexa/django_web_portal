from django.urls import path
from .views import ComplaintListCreateView


urlpatterns = [
    path('', ComplaintListCreateView.as_view(), name='complaints'),
    # path('<int:pk>/status/', ComplaintStatusUpdateView.as_view(), name='update-complaint-status'),
]
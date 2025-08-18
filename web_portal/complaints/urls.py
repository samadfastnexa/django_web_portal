from django.urls import path
from .views import ComplaintListCreateView,ComplaintRetrieveUpdateView


urlpatterns = [
    # for listing and creating complaints (GET, POST).
     path('', ComplaintListCreateView.as_view(), name='complaint-list-create'),
    #  for retrieving and updating complaints (GET, PUT, PATCH).
    path('<int:pk>/', ComplaintRetrieveUpdateView.as_view(), name='complaint-detail-update'),
    # path('', ComplaintListCreateView.as_view(), name='complaints'),
    # path('<int:pk>/status/', ComplaintStatusUpdateView.as_view(), name='update-complaint-status'),
]
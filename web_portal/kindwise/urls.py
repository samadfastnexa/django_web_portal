from django.urls import path
from . import views

urlpatterns = [
    path('identify/', views.identify_view, name='kindwise_identify'),
    path('records/', views.records_by_user, name='kindwise_records_by_user'),
    path('records/<int:record_id>/', views.record_detail, name='kindwise_record_detail'),
]

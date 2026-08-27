from django.urls import path

from .views import GenerateReportView

urlpatterns = [
    path("generate", GenerateReportView.as_view(), name="report-generate"),
]

from django.urls import path
from . import views

app_name = "crop_manage"

urlpatterns = [
    path("reports/", views.reports_index, name="reports_index"),
    path("reports/weed-efficacy/", views.weed_efficacy_report, name="weed_efficacy_report"),
]

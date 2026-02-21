from django.urls import path

from .views import chart_data_view, dashboard_view

app_name = "dashboard"

urlpatterns = [
    path("", dashboard_view, name="home"),
    path("api/chart-data/", chart_data_view, name="chart_data"),
]

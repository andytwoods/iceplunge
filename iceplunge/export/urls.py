from django.urls import path

from .views import full_json_export_view, session_csv_export_view, trial_csv_export_view

app_name = "export"

urlpatterns = [
    path("sessions.csv", session_csv_export_view, name="session_csv"),
    path("trials.csv", trial_csv_export_view, name="trial_csv"),
    path("full.json", full_json_export_view, name="full_json"),
]

from django.urls import path

from .views import notification_preferences_view
from .views import register_device_view

app_name = "notifications"
urlpatterns = [
    path("register-device/", view=register_device_view, name="register_device"),
    path("preferences/", view=notification_preferences_view, name="preferences"),
]

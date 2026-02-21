from django.urls import path

from .views import plunge_create_view
from .views import plunge_delete_view
from .views import plunge_form_view
from .views import plunge_list_view

app_name = "plunges"
urlpatterns = [
    path("", view=plunge_list_view, name="list"),
    path("form/", view=plunge_form_view, name="form"),
    path("create/", view=plunge_create_view, name="create"),
    path("<int:pk>/delete/", view=plunge_delete_view, name="delete"),
]

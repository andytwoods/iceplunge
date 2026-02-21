from django.urls import path

from .views import baseline_profile_view
from .views import consent_view
from .views import data_deletion_complete_view
from .views import data_deletion_view
from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("consent/", view=consent_view, name="consent"),
    path("baseline/", view=baseline_profile_view, name="baseline_profile"),
    path("delete-my-data/", view=data_deletion_view, name="delete_data"),
    path("delete-my-data/done/", view=data_deletion_complete_view, name="deletion_complete"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
]

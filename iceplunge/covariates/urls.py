from django.urls import path

from .views import daily_covariate_view
from .views import more_info_view
from .views import weekly_covariate_view

app_name = "covariates"
urlpatterns = [
    path("daily/", view=daily_covariate_view, name="daily"),
    path("weekly/", view=weekly_covariate_view, name="weekly"),
    path("more-info/", view=more_info_view, name="more_info"),
]

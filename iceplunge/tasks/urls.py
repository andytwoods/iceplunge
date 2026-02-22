from django.urls import path

from .views import (
    session_complete_view,
    session_hub_view,
    session_meta_view,
    session_start_view,
    session_task_skip_view,
    session_task_view,
    task_result_submit_view,
    try_task_view,
)

app_name = "tasks"
urlpatterns = [
    path("start/", view=session_start_view, name="start"),
    path("try/<str:task_type>/", view=try_task_view, name="try_task"),
    path("session/<uuid:session_id>/hub/", view=session_hub_view, name="hub"),
    path("session/<uuid:session_id>/task/", view=session_task_view, name="task"),
    path("session/<uuid:session_id>/complete/", view=session_complete_view, name="complete"),
    path("api/submit-result/", view=task_result_submit_view, name="submit_result"),
    path("api/session-meta/", view=session_meta_view, name="session_meta"),
    path("api/skip-task/", view=session_task_skip_view, name="skip_task"),
]

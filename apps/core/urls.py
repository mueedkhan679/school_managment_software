from django.urls import path
from . import reports_views, views, purge_views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("reports/", reports_views.financial_reports, name="reports"),
    path("api/class/<int:class_id>/students/", views.api_class_students, name="api_class_students"),
    path("api/student/<str:student_id>/profile/", views.api_student_profile, name="api_student_profile"),
    path("settings/system-reset/", purge_views.system_reset, name="system_reset"),
]


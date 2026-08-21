from django.urls import path
from . import teacher_portal_views as views

app_name = "teacher_portal"

urlpatterns = [
    path("", views.teacher_dashboard, name="dashboard"),
    path("mark/", views.teacher_mark_attendance, name="mark"),
    path("history/", views.teacher_attendance_history, name="history"),
]

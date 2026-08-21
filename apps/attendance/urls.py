from django.urls import path
from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.admin_attendance_list, name="admin_attendance"),
    path("mark/", views.admin_attendance_mark, name="admin_attendance_mark"),
]

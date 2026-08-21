from django.urls import path
from . import student_portal_views as views

app_name = "student_portal"

urlpatterns = [
    path("", views.student_dashboard, name="dashboard"),
    path("fees/", views.student_fees, name="fees"),
    path("attendance/", views.student_attendance, name="attendance"),
]

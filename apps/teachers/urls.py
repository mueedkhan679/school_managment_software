from django.urls import path
from . import views

app_name = "teachers"

urlpatterns = [
    # Static and sub-resource routes first
    path("", views.teacher_list, name="list"),
    path("create/", views.teacher_create, name="create"),
    path("salaries/", views.salary_list, name="salary_list"),
    path("salaries/create/", views.salary_create, name="salary_create"),
    path("salaries/<int:pk>/", views.salary_voucher, name="salary_voucher"),
    path("salaries/<int:pk>/edit/", views.salary_update, name="salary_update"),
    path("salaries/<int:pk>/delete/", views.salary_delete, name="salary_delete"),
    # Teacher Attendance QR (must precede the <str:teacher_id> catch-all)
    path("attendance/qr/", views.teacher_attendance_qr_page, name="attendance_qr"),
    path("attendance/qr.png", views.teacher_attendance_qr_png, name="attendance_qr_png"),
    path("attendance/", views.teacher_attendance_list, name="attendance_list"),
    path("api/teacher-info/<int:teacher_id>/", views.api_teacher_salary_info, name="api_teacher_salary_info"),
    # Teacher ID parametrized routes
    path("<str:teacher_id>/", views.teacher_detail, name="detail"),
    path("<str:teacher_id>/edit/", views.teacher_update, name="update"),
    path("<str:teacher_id>/delete/", views.teacher_delete, name="delete"),
    path("<str:teacher_id>/restore/", views.teacher_restore, name="restore"),
]

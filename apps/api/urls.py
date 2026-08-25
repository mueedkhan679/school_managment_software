from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    StudentAttendanceView,
    StudentFeeView,
    StudentLoginView,
    StudentProfileView,
    TeacherAttendanceScanView,
    TeacherAttendanceView,
    TeacherSalaryView,
)

app_name = "api"

urlpatterns = [
    # Auth endpoints
    path("auth/login/", StudentLoginView.as_view(), name="student-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Student portal endpoints
    path("students/profile/", StudentProfileView.as_view(), name="student-profile"),
    path("students/attendance/", StudentAttendanceView.as_view(), name="student-attendance"),
    path("students/fees/", StudentFeeView.as_view(), name="student-fees"),

    # Teacher portal endpoints
    path("teacher/attendance/", TeacherAttendanceView.as_view(), name="teacher-attendance"),
    # Dynamic QR self check-in for teachers (POST)
    path("teacher/attendance/scan/", TeacherAttendanceScanView.as_view(), name="teacher-attendance-scan"),
    path("teachers/attendance/scan/", TeacherAttendanceScanView.as_view(), name="teachers-attendance-scan"),
    path("teacher/salary/", TeacherSalaryView.as_view(), name="teacher-salary"),
]

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    StudentAttendanceView,
    StudentFeeView,
    StudentLoginView,
    StudentProfileView,
    TeacherClassListView,
    TeacherAttendanceScanView,
    TeacherAttendanceView,
    TeacherLatestScanView,
    TeacherProfileApiView,
    TeacherSalaryView,
    TeacherStudentCreateView,
    ChangePasswordView,
    NotificationListView,
    NotificationClearView,
    UpdateFcmTokenView,
)

app_name = "api"

urlpatterns = [
    # Auth endpoints
    path("auth/login/", StudentLoginView.as_view(), name="student-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("update-fcm-token/", UpdateFcmTokenView.as_view(), name="update-fcm-token"),

    # Notifications
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path("notifications/clear/", NotificationClearView.as_view(), name="notification_clear"),

    # Student portal endpoints
    path("students/profile/", StudentProfileView.as_view(), name="student-profile"),
    path("students/attendance/", StudentAttendanceView.as_view(), name="student-attendance"),
    path("students/fees/", StudentFeeView.as_view(), name="student-fees"),

    # Teacher portal endpoints
    path("teacher/classes/", TeacherClassListView.as_view(), name="teacher-classes"),
    path("teacher/profile/", TeacherProfileApiView.as_view(), name="teacher-profile"),
    path("teacher/students/add/", TeacherStudentCreateView.as_view(), name="teacher-student-add"),
    path("teacher/attendance/", TeacherAttendanceView.as_view(), name="teacher-attendance"),
    # Dynamic QR self check-in for teachers (POST)
    path("teacher/attendance/scan/", TeacherAttendanceScanView.as_view(), name="teacher-attendance-scan"),
    path("teachers/attendance/scan/", TeacherAttendanceScanView.as_view(), name="teachers-attendance-scan"),
    # Real-time polling: latest scan + live counters (GET)
    path("teacher/attendance/latest-scan/", TeacherLatestScanView.as_view(), name="teacher-latest-scan"),
    path("teachers/attendance/latest-scan/", TeacherLatestScanView.as_view(), name="teachers-latest-scan"),
    path("teacher/salary/", TeacherSalaryView.as_view(), name="teacher-salary"),
]

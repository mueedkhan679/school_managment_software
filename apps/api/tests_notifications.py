"""Regression tests: automatic parent/student notifications on attendance submission.

Covers:
- POST /api/v1/teacher/attendance/ creates a ``Notification`` (title
  ``"Attendance Update - <teacher name/username>"``) for every marked
  student that has a linked login account, plus a best-effort FCM push.
- Students without a linked account are skipped silently — the submission
  still succeeds and never crashes (the try/except guarantee).
- Resubmitting attendance for the same day UPDATES the single
  ``(student, date)`` record (once-per-day) instead of duplicating.
- Bad dates return 400 and empty submissions return 200/0 — no
  ``UnboundLocalError`` (HTTP 500) on any code path.
- GET /api/v1/notifications/ exposes both ``notifications`` and ``payload``
  keys; the Flutter student portal (``NotificationCenterView``) reads
  ``payload``.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.core.models import Notification
from apps.students.models import Gender, Student
from apps.teachers.models import Teacher

User = get_user_model()


class AttendanceNotificationTests(APITestCase):
    """POST /api/v1/teacher/attendance/ must notify linked students every time."""

    def setUp(self):
        self.cls = SchoolClass.objects.create(name="Notif Class", order=9)

        self.teacher_user = User.objects.create_user(
            username="notif_tch",
            password="teachpass123",
            role=Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            name="Mr. Notif",
            phone="03001112233",
            monthly_salary=Decimal("40000.00"),
            user=self.teacher_user,
        )

        # Student WITH a linked login account -> must receive notifications.
        self.student_user = User.objects.create_user(
            username="notif_stu",
            password="stupass123",
            role=Role.STUDENT,
        )
        self.student = Student.objects.create(
            name="Ali Khan",
            father_name="Khan Sr",
            school_class=self.cls,
            date_of_birth=date(2012, 3, 3),
            gender=Gender.MALE,
            user=self.student_user,
        )
        # Student WITHOUT a linked account -> silently skipped.
        self.student_no_user = Student.objects.create(
            name="No Account",
            father_name="None Sr",
            school_class=self.cls,
            date_of_birth=date(2012, 5, 5),
            gender=Gender.MALE,
        )

        self._login("notif_tch", "teachpass123")

    def _login(self, username, password):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _post_attendance(self, **overrides):
        data = {
            "class_id": self.cls.id,
            "date": "2026-09-01",
            "attendance": {
                str(self.student.id): "ABSENT",
                str(self.student_no_user.id): "PRESENT",
            },
        }
        data.update(overrides)
        return self.client.post(reverse("api:teacher-attendance"), data, format="json")

    # ------------------ Notification creation ------------------

    def test_submission_creates_notification_with_title_and_message(self):
        resp = self._post_attendance()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["payload"]["marked_count"], 2)

        notifs = Notification.objects.filter(user=self.student_user)
        self.assertEqual(notifs.count(), 1)
        notif = notifs.first()
        # setUp users have no first/last name, so get_full_name() is empty
        # and the username is used as the teacher display name.
        self.assertEqual(notif.title, "Attendance Update - notif_tch")
        self.assertEqual(
            notif.message, "notif_tch marked your attendance as ABSENT for 2026-09-01."
        )

    def test_student_without_linked_account_is_skipped_silently(self):
        """Missing ``Student.user`` must never break the submission flow."""
        resp = self._post_attendance()
        self.assertEqual(resp.status_code, 200)
        # Only the linked student received a notification.
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Notification.objects.first().user, self.student_user)

    # ------------------ Once-per-day behaviour ------------------

    def test_resubmission_updates_record_and_notifies_again(self):
        self._post_attendance()
        resp = self._post_attendance(
            attendance={str(self.student.id): "PRESENT"}
        )
        self.assertEqual(resp.status_code, 200)

        rows = Attendance.objects.filter(student=self.student, date=date(2026, 9, 1))
        self.assertEqual(rows.count(), 1)  # no duplicates
        self.assertEqual(rows.first().status, AttendanceStatus.PRESENT)

        # A fresh notification is generated for the update as well.
        self.assertEqual(
            Notification.objects.filter(user=self.student_user).count(), 2
        )

    # ------------------ No UnboundLocalError on edge paths ------------------

    def test_invalid_date_returns_400(self):
        resp = self._post_attendance(date="not-a-date")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Attendance.objects.count(), 0)

    def test_blank_or_missing_date_defaults_to_today(self):
        """``date: ""``/``null``/absent all fall back to the server's today."""
        for blank in ("", None):
            Attendance.objects.all().delete()
            Notification.objects.all().delete()
            resp = self._post_attendance(date=blank)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(
                Attendance.objects.filter(
                    student=self.student, date=date.today()
                ).count(),
                1,
            )
        # Omitting the key entirely behaves the same way.
        data = {
            "class_id": self.cls.id,
            "attendance": {str(self.student.id): "PRESENT"},
        }
        resp = self.client.post(
            reverse("api:teacher-attendance"), data, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Attendance.objects.filter(student=self.student, date=date.today()).count(),
            1,
        )

    def test_empty_submission_marks_nothing(self):
        resp = self._post_attendance(attendance={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["payload"]["marked_count"], 0)
        self.assertEqual(Attendance.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    # ------------------ Notifications list endpoint ------------------

    def test_notification_list_returns_payload_mirror_with_title(self):
        self._post_attendance()

        # Log in as the student and read their notifications.
        self._login("notif_stu", "stupass123")
        resp = self.client.get(reverse("api:notification_list"))
        self.assertEqual(resp.status_code, 200)

        body = resp.json()
        # Both keys present — web reads ``notifications``, Flutter reads ``payload``.
        self.assertIn("notifications", body)
        self.assertIn("payload", body)
        self.assertEqual(body["payload"], body["notifications"])
        self.assertEqual(len(body["payload"]), 1)
        self.assertEqual(body["payload"][0]["title"], "Attendance Update - notif_tch")
        self.assertEqual(
            body["payload"][0]["message"],
            "notif_tch marked your attendance as ABSENT for 2026-09-01.",
        )

    # ------------------ FCM push architecture ------------------

    def test_send_fcm_notification_without_token_returns_false(self):
        """Users without a registered ``fcm_token`` are a safe no-op."""
        from apps.core.fcm import send_fcm_notification

        self.assertFalse(send_fcm_notification(self.teacher_user, "Title", "Body"))

    @override_settings(FIREBASE_CREDENTIALS_PATH=None)
    def test_attendance_flow_survives_unconfigured_fcm(self):
        """A registered FCM token without Firebase credentials must never
        break the submission — the DB notification is still created."""
        self.student_user.fcm_token = "device-token-abc123"
        self.student_user.save(update_fields=["fcm_token"])

        resp = self._post_attendance()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(
            Notification.objects.first().title, "Attendance Update - notif_tch"
        )


class FcmRegistrationTests(APITestCase):
    """POST /api/v1/update-fcm-token/ registers the device push token."""

    def setUp(self):
        # The login endpoint enforces role-based profile validation
        # (CustomTokenObtainPairSerializer.validate), so a STUDENT account
        # must have an active Student profile before it can obtain a token.
        self.cls = SchoolClass.objects.create(name="FCM Class", order=10)
        self.user = User.objects.create_user(
            username="fcm_user",
            password="fcmpass123",
            role=Role.STUDENT,
        )
        Student.objects.create(
            name="FCM Tester",
            father_name="Test Sr",
            school_class=self.cls,
            date_of_birth=date(2012, 1, 1),
            gender=Gender.MALE,
            user=self.user,
        )

    def _login(self):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": "fcm_user", "password": "fcmpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_registers_token_when_authenticated(self):
        self._login()
        resp = self.client.post(
            reverse("api:update-fcm-token"),
            {"fcm_token": "device-token-abc123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")
        self.user.refresh_from_db()
        self.assertEqual(self.user.fcm_token, "device-token-abc123")

    def test_missing_token_returns_400(self):
        self._login()
        resp = self.client.post(reverse("api:update-fcm-token"), {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_overlong_token_returns_400(self):
        self._login()
        resp = self.client.post(
            reverse("api:update-fcm-token"),
            {"fcm_token": "x" * 256},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_requires_authentication(self):
        resp = self.client.post(
            reverse("api:update-fcm-token"),
            {"fcm_token": "tok"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

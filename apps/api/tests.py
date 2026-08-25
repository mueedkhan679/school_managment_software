"""API tests: student profile endpoint exposes admission_fee for Flutter."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from django.utils import timezone

from apps.accounts.models import Role
from apps.attendance.qr_tokens import generate_token
from apps.classrooms.models import SchoolClass
from apps.students.models import Gender, Student
from apps.teachers.models import Teacher, TeacherAttendance

User = get_user_model()


class StudentProfileAdmissionFeeAPITests(APITestCase):
    """GET /api/v1/students/profile/ includes admission_fee for the app."""

    def setUp(self):
        self.cls = SchoolClass.objects.create(name="Class API", order=90)
        self.user = User.objects.create_user(
            username="stu_user",
            password="stupass123",
            role=Role.STUDENT,
        )
        self.student = Student.objects.create(
            name="Ali Khan",
            father_name="Tariq Khan",
            school_class=self.cls,
            date_of_birth=date(2015, 5, 12),
            gender=Gender.MALE,
            admission_fee=Decimal("5000.00"),
            user=self.user,
        )

    def _authenticate(self):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": "stu_user", "password": "stupass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_profile_includes_admission_fee_amount(self):
        """A recorded admission fee serializes into the profile payload."""
        self._authenticate()
        resp = self.client.get(reverse("api:student-profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")
        self.assertEqual(resp.json()["payload"]["admission_fee"], "5000.00")

    def test_admission_fee_none_serializes_as_null(self):
        """A missing/waived admission fee serializes as null."""
        self.student.admission_fee = None
        self.student.save(update_fields=["admission_fee"])
        self._authenticate()
        resp = self.client.get(reverse("api:student-profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["payload"]["admission_fee"])

    def test_profile_requires_authentication(self):
        """Anonymous requests are rejected with 401."""
        resp = self.client.get(reverse("api:student-profile"))
        self.assertEqual(resp.status_code, 401)

    def test_login_by_student_id_also_works(self):
        """App users may authenticate via their STU-* registration ID."""
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": self.student.student_id, "password": "stupass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get(reverse("api:student-profile"))
        self.assertEqual(resp.json()["payload"]["admission_fee"], "5000.00")


class TeacherAttendanceScanAPITests(APITestCase):
    """POST /api/v1/teacher/attendance/scan/ end-to-end behaviour."""

    def setUp(self):
        self.cls = SchoolClass.objects.create(name="Class T", order=95)

        # Teacher with linked login account
        self.teacher_user = User.objects.create_user(
            username="tch_user",
            password="teachpass123",
            role=Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            name="Prof. Snape",
            phone="03001112233",
            monthly_salary=Decimal("45000.00"),
            user=self.teacher_user,
        )

        # A student-linked user must never be able to scan
        self.student_user = User.objects.create_user(
            username="stu_gate",
            password="stupass123",
            role=Role.STUDENT,
        )
        Student.objects.create(
            name="Gate Keeper",
            father_name="No Entry",
            school_class=self.cls,
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            user=self.student_user,
        )

    def _login(self, username, password):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _scan(self, token):
        return self.client.post(
            reverse("api:teacher-attendance-scan"),
            {"token": token},
            format="json",
        )

    def test_valid_token_marks_attendance_with_time_in(self):
        """First scan creates a Present record and reports the check-in time."""
        self._login("tch_user", "teachpass123")
        resp = self._scan(generate_token(timezone.localdate()))
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertTrue(
            body["message"].startswith("Attendance marked successfully at")
        )
        record = TeacherAttendance.objects.get(teacher=self.teacher)
        self.assertEqual(record.status, "PRESENT")
        self.assertIsNotNone(record.time_in)
        self.assertEqual(record.source, "QR")

    def test_duplicate_scan_is_idempotent(self):
        """Second scan does not duplicate; it reports the original time."""
        self._login("tch_user", "teachpass123")
        first = self._scan(generate_token(timezone.localdate()))
        original_time = first.json()["payload"]["time_in"]

        second = self._scan(generate_token(timezone.localdate()))
        self.assertEqual(second.status_code, 200)
        self.assertIn("already marked", second.json()["message"])
        self.assertTrue(second.json()["payload"]["duplicate"])
        self.assertEqual(TeacherAttendance.objects.count(), 1)
        self.assertEqual(
            TeacherAttendance.objects.first().time_in.strftime("%H:%M:%S"),
            original_time,
        )

    def test_tampered_token_rejected(self):
        """A forged signature is rejected with a 400 error."""
        self._login("tch_user", "teachpass123")
        bad_token = generate_token(timezone.localdate())[:-4] + "0000"
        resp = self._scan(bad_token)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["status"], "error")
        self.assertFalse(TeacherAttendance.objects.exists())

    def test_expired_yesterday_token_rejected(self):
        """Yesterday's dashboard code no longer works."""
        from datetime import timedelta

        yesterday = timezone.localdate() - timedelta(days=1)
        self._login("tch_user", "teachpass123")
        resp = self._scan(generate_token(yesterday))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("expired", resp.json()["message"])

    def test_student_accounts_cannot_scan(self):
        """Non-teacher accounts receive 403 and nothing is recorded."""
        self._login("stu_gate", "stupass123")
        resp = self._scan(generate_token(timezone.localdate()))
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(TeacherAttendance.objects.exists())

    def test_alias_route_works_too(self):
        """The task-specified /teachers/ spelling is an accepted alias."""
        self._login("tch_user", "teachpass123")
        resp = self.client.post(
            reverse("api:teachers-attendance-scan"),
            {"token": generate_token(timezone.localdate())},
            format="json",
        )
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(resp.json()["status"], "success")


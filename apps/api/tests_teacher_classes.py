"""API tests: any teacher can view ALL classes and mark attendance for any of them.

Covers:
- GET  /api/v1/teacher/classes/   -> full school class list with student counts
- GET  /api/v1/teacher/attendance/?class_id=...  -> roster for ANY class
- POST /api/v1/teacher/attendance/               -> save attendance for ANY class
- Audit trail: ``Attendance.marked_by`` always stores the requesting teacher's
  account so ``marked_by_teacher`` resolves on every record.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.students.models import Gender, Student
from apps.teachers.models import Teacher

User = get_user_model()


class TeacherAnyClassAccessTests(APITestCase):
    """Teachers are no longer restricted to their own assigned classes."""

    def setUp(self):
        # Two classes; the teacher is assigned NEITHER of them.
        self.cls_a = SchoolClass.objects.create(name="Class Alpha", order=1)
        self.cls_b = SchoolClass.objects.create(name="Class Beta", order=2)

        self.teacher_user = User.objects.create_user(
            username="any_tch",
            password="teachpass123",
            role=Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            name="Mr. Any Class",
            phone="03001234567",
            monthly_salary=Decimal("40000.00"),
            user=self.teacher_user,
        )

        self.student_a = Student.objects.create(
            name="Ali Khan",
            father_name="Khan Sr",
            school_class=self.cls_a,
            date_of_birth=date(2012, 3, 3),
            gender=Gender.MALE,
        )
        self.student_b = Student.objects.create(
            name="Sara Ahmed",
            father_name="Ahmed Sr",
            school_class=self.cls_b,
            date_of_birth=date(2013, 4, 4),
            gender=Gender.FEMALE,
        )

        self._login()

    def _login(self):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": "any_tch", "password": "teachpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _login_as(self, username, password):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ------------------ Class list endpoint ------------------

    def test_classes_endpoint_lists_every_active_class(self):
        """/teacher/classes/ returns all classes, not just assigned ones."""
        resp = self.client.get(reverse("api:teacher-classes"))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()["payload"]["classes"]
        names = [c["name"] for c in payload]
        self.assertIn(self.cls_a.name, names)
        self.assertIn(self.cls_b.name, names)
        counts = {c["name"]: c["student_count"] for c in payload}
        self.assertEqual(counts[self.cls_a.name], 1)
        self.assertEqual(counts[self.cls_b.name], 1)

    def test_classes_endpoint_requires_authentication(self):
        """Anonymous requests are rejected."""
        self.client.credentials()
        resp = self.client.get(reverse("api:teacher-classes"))
        self.assertEqual(resp.status_code, 401)

    # ------------------ Roster for any class ------------------

    def test_roster_returns_students_of_unassigned_class(self):
        """GET ?class_id= works for a class the teacher was never assigned."""
        resp = self.client.get(
            reverse("api:teacher-attendance"), {"class_id": self.cls_b.id}
        )
        self.assertEqual(resp.status_code, 200)
        roster = resp.json()["payload"]["roster"]
        ids = [s["id"] for s in roster]
        self.assertIn(self.student_b.id, ids)
        self.assertNotIn(self.student_a.id, ids)

    def test_roster_without_class_id_lists_all_students(self):
        """GET without class_id returns students from every class."""
        resp = self.client.get(reverse("api:teacher-attendance"))
        self.assertEqual(resp.status_code, 200)
        roster = resp.json()["payload"]["roster"]
        ids = [s["id"] for s in roster]
        self.assertIn(self.student_a.id, ids)
        self.assertIn(self.student_b.id, ids)

    # ------------------ Attendance for any class ------------------

    def test_post_attendance_for_unassigned_class_succeeds(self):
        """A teacher can mark attendance for any class and is recorded as marker."""
        resp = self.client.post(
            reverse("api:teacher-attendance"),
            {
                "class_id": self.cls_b.id,
                "date": date.today().strftime("%Y-%m-%d"),
                "attendance": {str(self.student_b.id): "ABSENT"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["payload"]["marked_count"], 1)

        record = Attendance.objects.get(student=self.student_b)
        self.assertEqual(record.status, AttendanceStatus.ABSENT)
        # The audit trail points at the requesting teacher.
        self.assertEqual(record.marked_by_id, self.teacher_user.id)
        self.assertIsNotNone(record.marked_by_teacher)
        self.assertEqual(record.marked_by_teacher.pk, self.teacher.pk)

    def test_post_attendance_does_not_touch_other_classes(self):
        """Scoping by class_id never writes students of other classes."""
        resp = self.client.post(
            reverse("api:teacher-attendance"),
            {
                "class_id": self.cls_a.id,
                "attendance": {str(self.student_a.id): "PRESENT"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Attendance.objects.count(), 1)
        self.assertEqual(Attendance.objects.first().student_id, self.student_a.id)

    def test_resubmission_updates_instead_of_duplicating(self):
        """Re-posting for the same day updates rows (unique per student+date)."""
        body_data = {
            "class_id": self.cls_a.id,
            "attendance": {str(self.student_a.id): "PRESENT"},
        }
        first = self.client.post(
            reverse("api:teacher-attendance"), body_data, format="json"
        )
        self.assertEqual(first.status_code, 200)

        body_data["attendance"] = {str(self.student_a.id): "ABSENT"}
        second = self.client.post(
            reverse("api:teacher-attendance"), body_data, format="json"
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Attendance.objects.count(), 1)
        record = Attendance.objects.get(student=self.student_a)
        self.assertEqual(record.status, AttendanceStatus.ABSENT)

    def test_student_accounts_cannot_mark_class_attendance(self):
        """Non-teacher accounts get 403 and nothing is written."""
        stu_user = User.objects.create_user(
            username="stu_block",
            password="stupass123",
            role=Role.STUDENT,
        )
        Student.objects.create(
            name="Blocker",
            father_name="No Entry",
            school_class=self.cls_a,
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            user=stu_user,
        )
        self._login_as("stu_block", "stupass123")
        resp = self.client.post(
            reverse("api:teacher-attendance"),
            {"class_id": self.cls_a.id, "attendance": {}},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Attendance.objects.exists())

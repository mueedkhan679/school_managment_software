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


class TeacherLeaveStatusTests(APITestCase):
    """The mobile API accepts LEAVE (Chhutti) alongside PRESENT/ABSENT."""

    def setUp(self):
        self.cls = SchoolClass.objects.create(name="Class L", order=3)
        self.teacher_user = User.objects.create_user(
            username="leave_tch",
            password="teachpass123",
            role=Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            name="Ms. Leave",
            phone="03009998887",
            monthly_salary=Decimal("35000.00"),
            user=self.teacher_user,
        )
        self.student = Student.objects.create(
            name="Chhutti Khan",
            father_name="Khan",
            school_class=self.cls,
            date_of_birth=date(2011, 6, 6),
            gender=Gender.MALE,
        )
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": "leave_tch", "password": "teachpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_post_leave_status_persists(self):
        """Submitting LEAVE saves a Leave record for the student."""
        resp = self.client.post(
            reverse("api:teacher-attendance"),
            {
                "class_id": self.cls.id,
                "attendance": {str(self.student.id): "LEAVE"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        record = Attendance.objects.get(student=self.student)
        self.assertEqual(record.status, AttendanceStatus.LEAVE)

    def test_invalid_status_still_ignored(self):
        """Unknown status strings are skipped (defaulted roster only)."""
        resp = self.client.post(
            reverse("api:teacher-attendance"),
            {
                "class_id": self.cls.id,
                "attendance": {str(self.student.id): "SICK"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        # Nothing persisted because SICK is not a valid choice.
        self.assertFalse(Attendance.objects.exists())


class TeacherStudentCreateTests(APITestCase):
    """POST /api/v1/teacher/students/add/ teacher-registers-a-student flow."""

    def setUp(self):
        self.cls = SchoolClass.objects.create(name="Class Add", order=5)
        self.other_cls = SchoolClass.objects.create(name="Class Other", order=6)
        self.teacher_user = User.objects.create_user(
            username="add_tch",
            password="teachpass123",
            role=Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            name="Mr. Add",
            phone="03003211223",
            monthly_salary=Decimal("45000.00"),
            user=self.teacher_user,
        )

    def _login_teacher(self):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": "add_tch", "password": "teachpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_teacher_creates_student(self):
        """A teacher can add a student with the required fields."""
        self._login_teacher()
        resp = self.client.post(
            reverse("api:teacher-student-add"),
            {
                "full_name": "New Kid",
                "roll_number": "R-101",
                "classroom_id": self.cls.id,
                "father_name": "Dad Name",
                "phone_number": "03112223344",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["message"], "Student added successfully!")
        payload = body["payload"]
        self.assertEqual(payload["name"], "New Kid")
        self.assertEqual(payload["father_name"], "Dad Name")
        self.assertEqual(payload["roll_number"], "R-101")
        self.assertEqual(payload["class_id"], self.cls.id)
        self.assertEqual(payload["phone"], "03112223344")
        # Student actually persisted
        student = Student.objects.get(school_class=self.cls, name="New Kid")
        self.assertTrue(student.is_active)
        self.assertEqual(student.roll_number, "R-101")
        # A login account was provisioned and linked automatically
        self.assertIsNotNone(student.user_id)
        self.assertEqual(student.user.username, "stu_R-101")
        self.assertEqual(student.user.role, Role.STUDENT)
        self.assertTrue(student.user.is_active)
        self.assertTrue(student.user.check_password("Student@123"))
        # The generated credentials are returned to the teacher
        self.assertEqual(payload["username"], "stu_R-101")
        self.assertEqual(payload["default_password"], "Student@123")

    def test_auto_account_username_suffix_on_collision(self):
        """An already-taken username gets a unique suffix, not a failure."""
        User.objects.create_user(
            username="stu_R-101",
            password="someotherpass123",
            role=Role.STUDENT,
        )
        self._login_teacher()
        resp = self.client.post(
            reverse("api:teacher-student-add"),
            {
                "full_name": "Second Kid",
                "roll_number": "R-101",
                "classroom_id": self.cls.id,
                "father_name": "Dad Two",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        student = Student.objects.get(name="Second Kid")
        self.assertIsNotNone(student.user_id)
        self.assertNotEqual(student.user.username, "stu_R-101")
        self.assertTrue(student.user.username.startswith("stu_R-101_"))
        self.assertTrue(student.user.check_password("Student@123"))

    def test_account_created_without_roll_number(self):
        """No roll number: the username falls back to the permanent student_id."""
        self._login_teacher()
        resp = self.client.post(
            reverse("api:teacher-student-add"),
            {
                "full_name": "No Roll Kid",
                "classroom_id": self.cls.id,
                "father_name": "Dad Three",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        student = Student.objects.get(name="No Roll Kid")
        self.assertIsNotNone(student.user_id)
        self.assertEqual(student.user.username, f"stu_{student.student_id}")
        payload = resp.json()["payload"]
        self.assertEqual(payload["username"], student.user.username)
        self.assertEqual(payload["default_password"], "Student@123")

    def test_roll_number_unique_within_class(self):
        """A duplicate roll number in the same class is rejected."""
        Student.objects.create(
            name="Existing",
            father_name="F",
            school_class=self.cls,
            roll_number="R-77",
            date_of_birth=date(2010, 1, 1),
            gender="M",
        )
        self._login_teacher()
        resp = self.client.post(
            reverse("api:teacher-student-add"),
            {
                "full_name": "New Kid",
                "roll_number": "R-77",
                "classroom_id": self.cls.id,
                "father_name": "Dad",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already exists", resp.json()["message"])
        self.assertEqual(Student.objects.count(), 1)

    def test_same_roll_number_allowed_in_other_class(self):
        """Roll numbers only need to be unique within each class."""
        self._login_teacher()
        resp = self.client.post(
            reverse("api:teacher-student-add"),
            {
                "full_name": "Ali",
                "roll_number": "R-9",
                "classroom_id": self.other_cls.id,
                "father_name": "Dad",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        resp2 = self.client.post(
            reverse("api:teacher-student-add"),
            {
                "full_name": "Zia",
                "roll_number": "R-9",
                "classroom_id": self.cls.id,
                "father_name": "Dad",
            },
            format="json",
        )
        self.assertEqual(resp2.status_code, 201)
        self.assertEqual(Student.objects.count(), 2)

    def test_admission_date_defaults_to_today(self):
        """When admission_date is omitted it defaults to the current date."""
        self._login_teacher()
        resp = self.client.post(
            reverse("api:teacher-student-add"),
            {
                "full_name": "New Kid",
                "roll_number": "R-1",
                "classroom_id": self.cls.id,
                "father_name": "Dad",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        student = Student.objects.get(roll_number="R-1")
        self.assertEqual(student.admission_date, date.today())

    def test_students_cannot_use_endpoint(self):
        """Non-teacher accounts get 403."""
        stu_user = User.objects.create_user(
            username="stu_add",
            password="stupass123",
            role=Role.STUDENT,
        )
        Student.objects.create(
            name="Blocker",
            father_name="No",
            school_class=self.cls,
            date_of_birth=date(2010, 1, 1),
            gender="M",
            user=stu_user,
        )
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": "stu_add", "password": "stupass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {resp.json()['payload']['access']}"
        )
        res = self.client.post(
            reverse("api:teacher-student-add"),
            {"full_name": "H", "classroom_id": self.cls.id, "father_name": "X"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)


class TeacherProfileApiTests(APITestCase):
    """GET /api/v1/teacher/profile/ powers the in-app Digital ID Card."""

    def setUp(self):
        self.cls = SchoolClass.objects.create(name="Class P", order=4)
        self.teacher_user = User.objects.create_user(
            username="profile_tch",
            password="teachpass123",
            role=Role.TEACHER,
        )
        self.teacher = Teacher.objects.create(
            name="Mr. Profile",
            phone="03005556667",
            address="1 School Lane",
            cnic="35201-1234567-1",
            monthly_salary=Decimal("50000.00"),
            user=self.teacher_user,
        )
        self.teacher.assigned_classes.add(self.cls)

    def _login(self, username, password):
        resp = self.client.post(
            reverse("api:student-login"),
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["payload"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_profile_returns_id_card_fields(self):
        """Photo/name/ID/designation/contact all serialize for the card."""
        self._login("profile_tch", "teachpass123")
        resp = self.client.get(reverse("api:teacher-profile"))
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()["payload"]
        self.assertEqual(payload["teacher_id"], self.teacher.teacher_id)
        self.assertEqual(payload["name"], "Mr. Profile")
        self.assertEqual(payload["designation"], "Teacher")
        self.assertEqual(payload["phone"], "03005556667")
        self.assertEqual(payload["address"], "1 School Lane")
        self.assertEqual(payload["cnic"], "35201-1234567-1")
        self.assertIsNone(payload["photo_url"])  # no picture uploaded
        class_names = [c["name"] for c in payload["assigned_classes"]]
        self.assertIn(self.cls.name, class_names)

    def test_profile_requires_authentication(self):
        """Anonymous requests are rejected."""
        resp = self.client.get(reverse("api:teacher-profile"))
        self.assertEqual(resp.status_code, 401)

    def test_students_cannot_fetch_teacher_profile(self):
        """Non-teacher accounts get 403."""
        stu_user = User.objects.create_user(
            username="stu_prof",
            password="stupass123",
            role=Role.STUDENT,
        )
        Student.objects.create(
            name="Prof Blocker",
            father_name="No Entry",
            school_class=self.cls,
            date_of_birth=date(2010, 2, 2),
            gender=Gender.FEMALE,
            user=stu_user,
        )
        self._login("stu_prof", "stupass123")
        resp = self.client.get(reverse("api:teacher-profile"))
        self.assertEqual(resp.status_code, 403)

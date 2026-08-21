from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import Student
from apps.teachers.models import Teacher

User = get_user_model()


class Phase11AdminAttendanceTests(TestCase):
    """Tests for Phase 11 - Admin Attendance Records & Management."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_test_user", password="adminpassword123", role=Role.ADMIN
        )
        self.school_class = SchoolClass.objects.create(name="Section 10A", monthly_fee=Decimal("1500.00"), order=100)
        self.other_class = SchoolClass.objects.create(name="Section 9B", monthly_fee=Decimal("1200.00"), order=101)

        self.student1 = Student.objects.create(
            name="Alice Smith",
            father_name="John Smith",
            school_class=self.school_class,
            date_of_birth=date(2010, 5, 12),
            gender="F",
        )
        self.student2 = Student.objects.create(
            name="Bob Jones",
            father_name="Robert Jones",
            school_class=self.school_class,
            date_of_birth=date(2010, 8, 20),
            gender="M",
        )

        self.today = date(2026, 8, 20)
        self.client.login(username="admin_test_user", password="adminpassword123")

    def test_admin_attendance_list_requires_admin(self):
        self.client.logout()
        # Anonymous redirected
        resp = self.client.get(reverse("attendance:admin_attendance"))
        self.assertRedirects(resp, f"{reverse('accounts:login')}?next={reverse('attendance:admin_attendance')}")

        # Student denied
        student_user = User.objects.create_user(username="stu1", password="pw", role=Role.STUDENT)
        self.client.login(username="stu1", password="pw")
        resp_stu = self.client.get(reverse("attendance:admin_attendance"))
        self.assertEqual(resp_stu.status_code, 403)

    def test_admin_attendance_list_filtering(self):
        Attendance.objects.create(
            student=self.student1, date=self.today, status=AttendanceStatus.PRESENT, marked_by=self.admin
        )
        Attendance.objects.create(
            student=self.student2, date=self.today, status=AttendanceStatus.ABSENT, marked_by=self.admin
        )

        resp = self.client.get(reverse("attendance:admin_attendance"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.student1.name)
        self.assertContains(resp, self.student2.name)

        # Filter by class
        resp_class = self.client.get(f"{reverse('attendance:admin_attendance')}?class_id={self.school_class.id}")
        self.assertContains(resp_class, self.student1.name)

        # Filter by student query
        resp_q = self.client.get(f"{reverse('attendance:admin_attendance')}?q={self.student1.student_id}")
        self.assertContains(resp_q, self.student1.name)
        self.assertNotIn(self.student2.name, resp_q.content.decode())

    def test_admin_attendance_mark_post(self):
        post_data = {
            "class_id": self.school_class.id,
            "date": "2026-08-20",
            f"status_{self.student1.id}": "PRESENT",
            f"status_{self.student2.id}": "ABSENT",
        }
        resp = self.client.post(reverse("attendance:admin_attendance_mark"), post_data)
        self.assertEqual(resp.status_code, 302)

        record1 = Attendance.objects.get(student=self.student1, date=self.today)
        self.assertEqual(record1.status, AttendanceStatus.PRESENT)
        self.assertEqual(record1.marked_by, self.admin)

        record2 = Attendance.objects.get(student=self.student2, date=self.today)
        self.assertEqual(record2.status, AttendanceStatus.ABSENT)

    def test_duplicate_attendance_constraint_handling(self):
        from django.db import transaction
        # Database constraint test
        Attendance.objects.create(student=self.student1, date=self.today, status=AttendanceStatus.PRESENT)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(student=self.student1, date=self.today, status=AttendanceStatus.ABSENT)

        # View handling via update_or_create (prevents crashing when re-marking)
        post_data = {
            "class_id": self.school_class.id,
            "date": "2026-08-20",
            f"status_{self.student1.id}": "ABSENT",
            f"status_{self.student2.id}": "PRESENT",
        }
        resp = self.client.post(reverse("attendance:admin_attendance_mark"), post_data)
        self.assertEqual(resp.status_code, 302)

        # Updated successfully without constraint violation
        self.assertEqual(Attendance.objects.get(student=self.student1, date=self.today).status, AttendanceStatus.ABSENT)

    def test_student_profile_links_attendance_stats(self):
        Attendance.objects.create(student=self.student1, date=date(2026, 8, 18), status=AttendanceStatus.PRESENT)
        Attendance.objects.create(student=self.student1, date=date(2026, 8, 19), status=AttendanceStatus.PRESENT)
        Attendance.objects.create(student=self.student1, date=date(2026, 8, 20), status=AttendanceStatus.ABSENT)

        resp = self.client.get(reverse("students:detail", kwargs={"student_id": self.student1.student_id}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Attendance Rate")
        self.assertContains(resp, "66.7%")


class Phase12TeacherPortalTests(TestCase):
    """Tests for Phase 12 - Teacher Portal App."""

    def setUp(self):
        self.school_class1 = SchoolClass.objects.create(name="Section 1X", monthly_fee=Decimal("1000.00"), order=102)
        self.school_class2 = SchoolClass.objects.create(name="Section 2Y", monthly_fee=Decimal("1200.00"), order=103)

        self.teacher_user = User.objects.create_user(username="teacher1", password="teacherpass123", role=Role.TEACHER)
        self.teacher_profile = Teacher.objects.create(
            name="Mr. Smith",
            phone="03001234567",
            monthly_salary=Decimal("50000.00"),
            user=self.teacher_user,
        )
        self.teacher_profile.assigned_classes.add(self.school_class1)

        self.student1 = Student.objects.create(
            name="Charlie Brown",
            father_name="David Brown",
            school_class=self.school_class1,
            date_of_birth=date(2012, 1, 1),
            gender="M",
        )
        self.student2 = Student.objects.create(
            name="Diana Prince",
            father_name="Bruce Prince",
            school_class=self.school_class2,
            date_of_birth=date(2012, 2, 2),
            gender="F",
        )

        self.client.login(username="teacher1", password="teacherpass123")

    def test_teacher_portal_dashboard(self):
        resp = self.client.get(reverse("teacher_portal:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Welcome, Mr. Smith!")
        self.assertContains(resp, self.school_class1.name)
        # Unassigned class should not be listed
        self.assertNotIn(self.school_class2.name, resp.content.decode())

    def test_teacher_access_control_denies_financials_and_admin(self):
        # Teacher denied fees page
        resp_fees = self.client.get(reverse("fees:list"))
        self.assertEqual(resp_fees.status_code, 403)

        # Teacher denied classrooms page
        resp_classes = self.client.get(reverse("classrooms:list"))
        self.assertEqual(resp_classes.status_code, 403)

        # Teacher denied user management page
        resp_manage = self.client.get(reverse("accounts:account_list"))
        self.assertEqual(resp_manage.status_code, 403)

    def test_teacher_mark_attendance_assigned_class(self):
        post_data = {
            "class_id": self.school_class1.id,
            "date": "2026-08-20",
            f"status_{self.student1.id}": "PRESENT",
        }
        resp = self.client.post(reverse("teacher_portal:mark"), post_data)
        self.assertEqual(resp.status_code, 302)

        record = Attendance.objects.get(student=self.student1, date=date(2026, 8, 20))
        self.assertEqual(record.status, AttendanceStatus.PRESENT)
        self.assertEqual(record.marked_by, self.teacher_user)

    def test_teacher_mark_attendance_unassigned_class_denied(self):
        post_data = {
            "class_id": self.school_class2.id,
            "date": "2026-08-20",
            f"status_{self.student2.id}": "PRESENT",
        }
        resp = self.client.post(reverse("teacher_portal:mark"), post_data)
        self.assertEqual(resp.status_code, 403)

    def test_teacher_attendance_history_unassigned_class_denied(self):
        resp = self.client.get(f"{reverse('teacher_portal:history')}?class_id={self.school_class2.id}")
        self.assertEqual(resp.status_code, 403)


class Phase13StudentPortalTests(TestCase):
    """Tests for Phase 13 - Student Portal App."""

    def setUp(self):
        self.school_class = SchoolClass.objects.create(name="Section 5Z", monthly_fee=Decimal("800.00"), order=104)
        self.student_user = User.objects.create_user(username="student1", password="studentpass123", role=Role.STUDENT)
        self.student_profile = Student.objects.create(
            name="Eve Adams",
            father_name="Frank Adams",
            school_class=self.school_class,
            date_of_birth=date(2015, 3, 15),
            gender="F",
            form_b_number="12345-6789012-3",
            user=self.student_user,
        )

        self.other_student_user = User.objects.create_user(username="student2", password="studentpass123", role=Role.STUDENT)
        self.other_student_profile = Student.objects.create(
            name="George Clark",
            father_name="Henry Clark",
            school_class=self.school_class,
            date_of_birth=date(2015, 4, 16),
            gender="M",
            user=self.other_student_user,
        )

        # Seed fee & attendance
        StudentFee.objects.create(
            student=self.student_profile,
            fee_month=8,
            fee_year=2026,
            amount=Decimal("800.00"),
            payment_date=date(2026, 8, 1),
            status=FeeStatus.PAID,
            reference="REC-202608-0001",
        )
        Attendance.objects.create(
            student=self.student_profile,
            date=date(2026, 8, 20),
            status=AttendanceStatus.PRESENT,
        )

        self.client.login(username="student1", password="studentpass123")

    def test_student_portal_dashboard(self):
        resp = self.client.get(reverse("student_portal:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Welcome, Eve Adams!")
        self.assertContains(resp, self.student_profile.student_id)
        self.assertContains(resp, "12345-6789012-3")
        # Other student's info must never be exposed
        self.assertNotIn(self.other_student_profile.name, resp.content.decode())

    def test_student_portal_fees(self):
        resp = self.client.get(reverse("student_portal:fees"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fee Summary & Ledger")
        self.assertContains(resp, "REC-202608-0001")
        self.assertContains(resp, "Rs 800.00")

    def test_student_portal_attendance(self):
        resp = self.client.get(reverse("student_portal:attendance"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Attendance Summary & Logs")
        self.assertContains(resp, "100.0%")
        self.assertContains(resp, "Present")

    def test_student_access_control_denies_admin_views(self):
        # Student denied admin student list
        resp = self.client.get(reverse("students:list"))
        self.assertEqual(resp.status_code, 403)

        # Student denied admin attendance page
        resp_att = self.client.get(reverse("attendance:admin_attendance"))
        self.assertEqual(resp_att.status_code, 403)

        # Student denied admin fee list
        resp_fees = self.client.get(reverse("fees:list"))
        self.assertEqual(resp_fees.status_code, 403)

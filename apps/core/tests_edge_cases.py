from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.fees.forms import StudentFeeForm
from apps.fees.models import FeeStatus, StudentFee
from apps.students.forms import StudentForm
from apps.students.models import Gender, Student
from apps.teachers.forms import TeacherForm, TeacherSalaryForm
from apps.teachers.models import SalaryStatus, Teacher, TeacherSalary

User = get_user_model()


class EdgeCaseAndSecurityTests(TestCase):
    """Comprehensive test suite for Phase 14 (Security) & Phase 15 (Edge Cases)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="sec_admin", password="password123", role=Role.ADMIN
        )
        self.teacher_user = User.objects.create_user(
            username="sec_teacher", password="password123", role=Role.TEACHER
        )
        self.student_user = User.objects.create_user(
            username="sec_student", password="password123", role=Role.STUDENT
        )

        self.school_class = SchoolClass.objects.create(
            name="Section Edge-1", monthly_fee=Decimal("2000.00"), order=200
        )
        self.student = Student.objects.create(
            name="Edge Student",
            father_name="Edge Father",
            school_class=self.school_class,
            date_of_birth=date(2012, 1, 1),
            gender=Gender.MALE,
            user=self.student_user,
        )

        self.teacher = Teacher.objects.create(
            name="Edge Teacher",
            phone="03009998877",
            monthly_salary=Decimal("50000.00"),
            user=self.teacher_user,
        )
        self.teacher.assigned_classes.add(self.school_class)

        cache.clear()

    def test_zero_and_negative_fee_and_salary_validation(self):
        """Verify form validation and DB constraints block zero or negative financial values."""
        # 1. Custom monthly fee negative check on StudentForm
        form_data = {
            "name": "Test Stu",
            "father_name": "Test Father",
            "school_class": self.school_class.id,
            "date_of_birth": "2015-05-05",
            "gender": "M",
            "custom_monthly_fee": "-500.00",
        }
        form = StudentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("custom_monthly_fee", form.errors)

        # 2. StudentFee negative amount check on StudentFeeForm
        fee_form_data = {
            "student": self.student.id,
            "fee_month": 8,
            "fee_year": 2026,
            "amount": "0.00",
            "payment_date": "2026-08-20",
            "status": FeeStatus.PAID,
        }
        fee_form = StudentFeeForm(data=fee_form_data)
        self.assertFalse(fee_form.is_valid())
        self.assertIn("amount", fee_form.errors)

        # 3. DB CheckConstraint fee_amount_positive
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentFee.objects.create(
                    student=self.student,
                    fee_month=8,
                    fee_year=2026,
                    amount=Decimal("0.00"),
                    payment_date=date(2026, 8, 20),
                    status=FeeStatus.PAID,
                )

        # 4. Teacher salary negative check on TeacherForm
        teacher_form_data = {
            "name": "Bad Salary Teacher",
            "phone": "03001111111",
            "monthly_salary": "0.00",
        }
        teacher_form = TeacherForm(data=teacher_form_data)
        self.assertFalse(teacher_form.is_valid())
        self.assertIn("monthly_salary", teacher_form.errors)

        # 5. TeacherSalary zero/negative check on TeacherSalaryForm
        sal_form_data = {
            "teacher": self.teacher.id,
            "salary_month": 8,
            "salary_year": 2026,
            "amount": "-100.00",
            "payment_date": "2026-08-20",
            "status": SalaryStatus.PAID,
        }
        sal_form = TeacherSalaryForm(data=sal_form_data)
        self.assertFalse(sal_form.is_valid())
        self.assertIn("amount", sal_form.errors)

        # 6. DB CheckConstraint salary_amount_positive
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TeacherSalary.objects.create(
                    teacher=self.teacher,
                    salary_month=8,
                    salary_year=2026,
                    amount=Decimal("-500.00"),
                    payment_date=date(2026, 8, 20),
                    status=SalaryStatus.PAID,
                )

    def test_duplicate_protection_under_database_constraints(self):
        """Verify DB unique constraints block duplicate fee, salary, and attendance records."""
        today = date(2026, 8, 20)

        # Duplicate Student Fee
        StudentFee.objects.create(
            student=self.student,
            fee_month=8,
            fee_year=2026,
            amount=Decimal("2000.00"),
            payment_date=today,
            status=FeeStatus.PAID,
            is_extra=False,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudentFee.objects.create(
                    student=self.student,
                    fee_month=8,
                    fee_year=2026,
                    amount=Decimal("2000.00"),
                    payment_date=today,
                    status=FeeStatus.PAID,
                    is_extra=False,
                )

        # Duplicate Teacher Salary
        TeacherSalary.objects.create(
            teacher=self.teacher,
            salary_month=8,
            salary_year=2026,
            amount=Decimal("50000.00"),
            payment_date=today,
            status=SalaryStatus.PAID,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TeacherSalary.objects.create(
                    teacher=self.teacher,
                    salary_month=8,
                    salary_year=2026,
                    amount=Decimal("50000.00"),
                    payment_date=today,
                    status=SalaryStatus.PAID,
                )

        # Duplicate Attendance
        Attendance.objects.create(
            student=self.student,
            date=today,
            status=AttendanceStatus.PRESENT,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(
                    student=self.student,
                    date=today,
                    status=AttendanceStatus.PRESENT,
                )

    def test_soft_deleted_entities_retain_history(self):
        """Verify deactivating students or teachers preserves all financial vouchers & attendance logs."""
        today = date(2026, 8, 20)

        fee = StudentFee.objects.create(
            student=self.student,
            fee_month=8,
            fee_year=2026,
            amount=Decimal("2000.00"),
            payment_date=today,
            status=FeeStatus.PAID,
            reference="REC-SOFT-01",
        )
        att = Attendance.objects.create(
            student=self.student,
            date=today,
            status=AttendanceStatus.PRESENT,
        )

        sal = TeacherSalary.objects.create(
            teacher=self.teacher,
            salary_month=8,
            salary_year=2026,
            amount=Decimal("50000.00"),
            payment_date=today,
            status=SalaryStatus.PAID,
            reference="SAL-SOFT-01",
        )

        # Deactivate student & teacher
        self.student.is_active = False
        self.student.save()

        self.teacher.is_active = False
        self.teacher.save()

        # Records remain queryable and intact in DB
        self.assertEqual(StudentFee.objects.get(pk=fee.pk).amount, Decimal("2000.00"))
        self.assertEqual(Attendance.objects.get(pk=att.pk).status, AttendanceStatus.PRESENT)
        self.assertEqual(TeacherSalary.objects.get(pk=sal.pk).amount, Decimal("50000.00"))

    def test_non_admin_rbac_matrix_denials(self):
        """Verify non-admin roles receive 403 Forbidden across all protected admin endpoints."""
        admin_endpoints = [
            reverse("core:dashboard"),
            reverse("core:reports"),
            reverse("classrooms:list"),
            reverse("students:list"),
            reverse("teachers:list"),
            reverse("fees:list"),
            reverse("attendance:admin_attendance"),
            reverse("accounts:account_list"),
        ]

        # Log in as Teacher
        self.client.login(username="sec_teacher", password="password123")
        for url in admin_endpoints:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, f"Teacher allowed access to admin route {url}")

        self.client.logout()

        # Log in as Student
        self.client.login(username="sec_student", password="password123")
        for url in admin_endpoints:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, f"Student allowed access to admin route {url}")

    def test_login_rate_limiting_lockout(self):
        """Verify 5 consecutive failed login attempts trigger lockout error."""
        login_url = reverse("accounts:login")
        bad_credentials = {"username": "sec_admin", "password": "wrongpassword"}

        # Perform 5 failed login attempts
        for i in range(5):
            resp = self.client.post(login_url, bad_credentials)
            self.assertEqual(resp.status_code, 200)

        # 6th attempt must trigger rate limit lockout error
        resp_lockout = self.client.post(login_url, bad_credentials)
        self.assertEqual(resp_lockout.status_code, 200)
        self.assertContains(resp_lockout, "Too many failed login attempts")

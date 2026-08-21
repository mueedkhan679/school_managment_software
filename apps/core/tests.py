from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import Gender, Student
from apps.teachers.models import SalaryStatus, Teacher, TeacherSalary

User = get_user_model()


class DashboardTestCase(TestCase):
    def setUp(self):
        # Admin user
        self.admin = User.objects.create_user(
            username="admin_user",
            password="adminpassword123",
            role=Role.ADMIN,
        )
        # Teacher user
        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="teacherpassword123",
            role=Role.TEACHER,
        )

        # Classes (seeded by migration, get or create and set monthly fees)
        self.cls1, _ = SchoolClass.objects.get_or_create(
            name="Class 1", defaults={"order": 4, "monthly_fee": Decimal("1500.00")}
        )
        self.cls1.monthly_fee = Decimal("1500.00")
        self.cls1.save()

        self.cls2, _ = SchoolClass.objects.get_or_create(
            name="Class 2", defaults={"order": 5, "monthly_fee": Decimal("2000.00")}
        )
        self.cls2.monthly_fee = Decimal("2000.00")
        self.cls2.save()

        # Students
        self.stu1 = Student.objects.create(
            name="Ali Khan",
            father_name="Tariq Khan",
            school_class=self.cls1,
            date_of_birth=date(2015, 5, 12),
            gender=Gender.MALE,
            phone="03001234567",
            email="ali@example.com",
            address="Street 1, Lahore",
            is_active=True,
        )
        self.stu2 = Student.objects.create(
            name="Sara Ahmed",
            father_name="Ahmed Bilal",
            school_class=self.cls1,
            date_of_birth=date(2016, 2, 20),
            gender=Gender.FEMALE,
            custom_monthly_fee=Decimal("1200.00"),  # custom fee override
            is_active=True,
        )
        self.stu_inactive = Student.objects.create(
            name="Zubair Malik",
            father_name="Malik Aslam",
            school_class=self.cls2,
            date_of_birth=date(2014, 8, 10),
            gender=Gender.MALE,
            is_active=False,
        )

        # Teachers
        self.tch1 = Teacher.objects.create(
            name="Prof. Usman",
            phone="03129876543",
            monthly_salary=Decimal("45000.00"),
            is_active=True,
        )
        self.tch1.assigned_classes.add(self.cls1)

        self.tch_inactive = Teacher.objects.create(
            name="Former Teacher",
            phone="03009999999",
            monthly_salary=Decimal("30000.00"),
            is_active=False,
        )

        self.now = timezone.now()
        self.year = self.now.year
        self.month = self.now.month
        self.today = self.now.date()

        # Fees
        # stu1 paid this month: 1500
        StudentFee.objects.create(
            student=self.stu1,
            fee_month=self.month,
            fee_year=self.year,
            amount=Decimal("1500.00"),
            payment_date=self.today,
            status=FeeStatus.PAID,
            reference="REC-001",
        )
        # stu2 paid this month: 1200
        StudentFee.objects.create(
            student=self.stu2,
            fee_month=self.month,
            fee_year=self.year,
            amount=Decimal("1200.00"),
            payment_date=self.today,
            status=FeeStatus.PAID,
            reference="REC-002",
        )
        # Pending fee (should NOT be added to paid income)
        StudentFee.objects.create(
            student=self.stu1,
            fee_month=((self.month % 12) + 1),
            fee_year=self.year,
            amount=Decimal("1500.00"),
            payment_date=self.today,
            status=FeeStatus.PENDING,
            reference="REC-PEND",
            is_extra=True,
        )

        # Teacher Salary
        # Paid salary this month: 45000
        TeacherSalary.objects.create(
            teacher=self.tch1,
            salary_month=self.month,
            salary_year=self.year,
            amount=Decimal("45000.00"),
            payment_date=self.today,
            status=SalaryStatus.PAID,
            reference="SAL-001",
        )

        # Today's attendance
        Attendance.objects.create(
            student=self.stu1,
            date=self.today,
            status=AttendanceStatus.PRESENT,
        )
        Attendance.objects.create(
            student=self.stu2,
            date=self.today,
            status=AttendanceStatus.ABSENT,
        )

    def test_dashboard_anonymous_redirect(self):
        """Anonymous user is redirected to login with next param."""
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_dashboard_non_admin_forbidden(self):
        """Non-admin user gets 403 Forbidden."""
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_metrics_calculation(self):
        """Admin dashboard computes all active counts, fees, salaries, and attendance."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)

        ctx = response.context
        # Active counts
        self.assertEqual(ctx["total_students"], 2)  # stu1 and stu2 active, inactive ignored
        self.assertEqual(ctx["total_classes"], SchoolClass.objects.count())
        self.assertEqual(ctx["total_teachers"], 1)  # tch1 active

        # Fee calculations (1500 + 1200 = 2700)
        self.assertEqual(ctx["monthly_fee_income"], Decimal("2700.00"))
        self.assertEqual(ctx["yearly_fee_income"], Decimal("2700.00"))
        self.assertEqual(ctx["total_fee_income"], Decimal("2700.00"))

        # Teacher Salary calculations
        self.assertEqual(ctx["monthly_teacher_salary"], Decimal("45000.00"))
        self.assertEqual(ctx["yearly_teacher_salary"], Decimal("45000.00"))
        self.assertEqual(ctx["total_teacher_salary"], Decimal("45000.00"))

        # Balance calculations (2700 - 45000 = -42300)
        self.assertEqual(ctx["current_balance"], Decimal("-42300.00"))
        self.assertEqual(ctx["monthly_net_income"], Decimal("-42300.00"))
        self.assertEqual(ctx["yearly_net_income"], Decimal("-42300.00"))

        # Attendance calculation (1 present, 1 absent => 50.0%)
        self.assertEqual(ctx["today_marked_total"], 2)
        self.assertEqual(ctx["today_present"], 1)
        self.assertEqual(ctx["today_absent"], 1)
        self.assertEqual(ctx["attendance_percentage"], 50.0)

    def test_api_class_students_endpoint(self):
        """API class students endpoint returns student list for the given class."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("core:api_class_students", kwargs={"class_id": self.cls1.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["class_id"], self.cls1.id)
        self.assertEqual(data["class_name"], "Class 1")
        self.assertEqual(data["total_students"], 2)
        self.assertEqual(len(data["students"]), 2)

        student_ids = [s["student_id"] for s in data["students"]]
        self.assertIn(self.stu1.student_id, student_ids)
        self.assertIn(self.stu2.student_id, student_ids)

    def test_api_student_profile_endpoint(self):
        """API student profile endpoint returns comprehensive student profile with fees & attendance."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("core:api_student_profile", kwargs={"student_id": self.stu1.student_id})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["student_id"], self.stu1.student_id)
        self.assertEqual(data["name"], "Ali Khan")
        self.assertEqual(data["father_name"], "Tariq Khan")
        self.assertEqual(data["effective_monthly_fee"], 1500.0)
        self.assertEqual(data["yearly_expected_fee"], 18000.0)
        self.assertEqual(data["total_paid_fees"], 1500.0)
        self.assertEqual(data["current_year_paid"], 1500.0)
        self.assertEqual(data["current_year_pending"], 16500.0)
        self.assertEqual(data["present_count"], 1)
        self.assertEqual(data["absent_count"], 0)
        self.assertEqual(data["attendance_percentage"], 100.0)
        self.assertEqual(len(data["recent_fees"]), 1)
        self.assertEqual(len(data["recent_attendance"]), 1)

    def test_index_redirects_to_dashboard_when_authenticated(self):
        """Root index redirects logged-in admin directly to dashboard."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("core:dashboard"), response.url)


class FinancialReportsTestCase(TestCase):
    """Test suite for Phase 7 Financial Reports & Analytics."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_rep",
            password="adminpassword123",
            role=Role.ADMIN,
        )
        self.teacher_user = User.objects.create_user(
            username="teacher_rep",
            password="teacherpassword123",
            role=Role.TEACHER,
        )

        self.cls1, _ = SchoolClass.objects.get_or_create(
            name="Class 1",
            defaults={"order": 1, "monthly_fee": Decimal("1500.00")},
        )
        self.cls1.monthly_fee = Decimal("1500.00")
        self.cls1.save()

        self.cls2, _ = SchoolClass.objects.get_or_create(
            name="Class 2",
            defaults={"order": 2, "monthly_fee": Decimal("2000.00")},
        )
        self.cls2.monthly_fee = Decimal("2000.00")
        self.cls2.save()

        self.stu1 = Student.objects.create(
            name="Ali Khan",
            father_name="Tariq Khan",
            school_class=self.cls1,
            date_of_birth=date(2015, 5, 12),
            gender=Gender.MALE,
            is_active=True,
        )
        self.stu2 = Student.objects.create(
            name="Sara Ahmed",
            father_name="Ahmed Bilal",
            school_class=self.cls2,
            date_of_birth=date(2016, 2, 20),
            gender=Gender.FEMALE,
            custom_monthly_fee=Decimal("1800.00"),
            is_active=True,
        )

        self.tch1 = Teacher.objects.create(
            name="Sir Usman",
            phone="03001112233",
            monthly_salary=Decimal("40000.00"),
            is_active=True,
        )

        self.now = timezone.now()
        self.year = self.now.year
        self.month = self.now.month
        self.today = self.now.date()

        # Fee payments: stu1 paid 1500, stu2 paid 1800 => 3300 total
        StudentFee.objects.create(
            student=self.stu1,
            fee_month=self.month,
            fee_year=self.year,
            amount=Decimal("1500.00"),
            payment_date=self.today,
            status=FeeStatus.PAID,
            reference="REC-REP-01",
        )
        StudentFee.objects.create(
            student=self.stu2,
            fee_month=self.month,
            fee_year=self.year,
            amount=Decimal("1800.00"),
            payment_date=self.today,
            status=FeeStatus.PAID,
            reference="REC-REP-02",
        )

        # Teacher Salary: 40000 paid
        TeacherSalary.objects.create(
            teacher=self.tch1,
            salary_month=self.month,
            salary_year=self.year,
            amount=Decimal("40000.00"),
            payment_date=self.today,
            status=SalaryStatus.PAID,
            reference="SAL-REP-01",
        )

    def test_reports_access_control(self):
        """Anonymous redirected to login; non-admins receive 403."""
        # Anonymous
        res = self.client.get(reverse("core:reports"))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse("accounts:login"), res.url)

        # Non-admin
        self.client.force_login(self.teacher_user)
        res = self.client.get(reverse("core:reports"))
        self.assertEqual(res.status_code, 403)

    def test_reports_kpi_metrics_and_profit_loss(self):
        """Financial reports dashboard accurately computes revenue, expenses, and net balance."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("core:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/reports.html")

        ctx = response.context
        # Collections: 1500 + 1800 = 3300
        self.assertEqual(ctx["today_fee_collection"], Decimal("3300.00"))
        self.assertEqual(ctx["month_fee_collection"], Decimal("3300.00"))
        self.assertEqual(ctx["year_fee_collection"], Decimal("3300.00"))

        # Expected Monthly Tuition: stu1 (1500) + stu2 (1800) = 3300
        self.assertEqual(ctx["expected_monthly_billing"], Decimal("3300.00"))
        self.assertEqual(ctx["expected_yearly_billing"], Decimal("39600.00"))

        # Year pending: 39600 - 3300 = 36300
        self.assertEqual(ctx["year_pending_fees"], Decimal("36300.00"))

        # Salary expenses: 40000
        self.assertEqual(ctx["month_salaries"], Decimal("40000.00"))
        self.assertEqual(ctx["year_salaries"], Decimal("40000.00"))

        # Net Profit/Loss: 3300 - 40000 = -36700
        self.assertEqual(ctx["month_net_income"], Decimal("-36700.00"))
        self.assertEqual(ctx["year_net_income"], Decimal("-36700.00"))
        self.assertEqual(ctx["annual_net_profit_loss"], Decimal("-36700.00"))

    def test_reports_class_filter(self):
        """Filtering by class computes isolated statistics for the selected class."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("core:reports") + f"?class_id={self.cls1.id}")
        self.assertEqual(response.status_code, 200)

        ctx = response.context
        # Class 1 only has stu1 (1500 fee)
        self.assertEqual(ctx["month_fee_collection"], Decimal("1500.00"))
        self.assertEqual(ctx["expected_monthly_billing"], Decimal("1500.00"))
        self.assertEqual(ctx["expected_yearly_billing"], Decimal("18000.00"))
        self.assertEqual(len(ctx["class_reports"]), 1)
        self.assertEqual(ctx["class_reports"][0]["class"].id, self.cls1.id)


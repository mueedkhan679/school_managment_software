import io
import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image as PILImage

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.core.models import SchoolSettings
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


class SchoolSettingsTests(TestCase):
    """Singleton SchoolSettings model, school_info context processor, and the
    School Settings configuration form on the Change Credentials page."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="branding_admin",
            password="brandingpass123",
            role=Role.ADMIN,
        )
        self.teacher_user = User.objects.create_user(
            username="branding_teacher",
            password="brandingteacher123",
            role=Role.TEACHER,
        )

    def test_load_creates_singleton_with_defaults(self):
        """SchoolSettings.load() lazily creates one row holding the defaults."""
        self.assertFalse(SchoolSettings.objects.exists())
        settings_obj = SchoolSettings.load()
        self.assertEqual(SchoolSettings.objects.count(), 1)
        self.assertEqual(settings_obj.pk, 1)
        self.assertEqual(settings_obj.school_name, SchoolSettings.DEFAULT_SCHOOL_NAME)
        # Second call must return the very same row, never duplicate it.
        self.assertEqual(SchoolSettings.load().pk, settings_obj.pk)

    def test_save_always_writes_the_single_row(self):
        """Every save writes to pk=1 so branding stays a single editable record."""
        first = SchoolSettings.load()
        first.school_name = "Al-Noor Public School"
        first.school_phone = "0300-1234567"
        first.save()
        second = SchoolSettings.load()
        second.school_name = "Iqbal Model High School"
        second.save()
        self.assertEqual(SchoolSettings.objects.count(), 1)
        self.assertEqual(SchoolSettings.objects.first().pk, 1)
        self.assertEqual(SchoolSettings.load().school_name, "Iqbal Model High School")

    def test_context_processor_exposes_branding(self):
        """school_info returns school_name/school_phone/school_logo for templates."""
        from apps.core.context_processors import school_info

        settings_obj = SchoolSettings.load()
        settings_obj.school_name = "Al-Noor Public School"
        settings_obj.school_phone = "042-111-222-333"
        settings_obj.save()

        info = school_info(request=None)
        self.assertEqual(info["school_name"], "Al-Noor Public School")
        self.assertEqual(info["school_phone"], "042-111-222-333")
        self.assertFalse(info["school_logo"])

    def test_change_credentials_page_shows_settings_form(self):
        """The Change Credentials page renders the School Settings panel with a
        multipart form (required for the logo upload) below credentials fields."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:change_credentials"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('enctype="multipart/form-data"', html)
        self.assertIn('name="save_settings"', html)
        self.assertIn('name="school_name"', html)
        self.assertIn('name="school_phone"', html)
        self.assertIn('name="school_logo"', html)
        # Credentials section still present alongside the settings panel.
        self.assertIn('name="current_password"', html)

    def test_change_credentials_page_requires_admin(self):
        """Anonymous users are redirected; teachers get 403."""
        res_anon = self.client.get(reverse("accounts:change_credentials"))
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn(reverse("accounts:login"), res_anon.url)

        self.client.force_login(self.teacher_user)
        res_teacher = self.client.get(reverse("accounts:change_credentials"))
        self.assertEqual(res_teacher.status_code, 403)

    def test_saving_school_settings_updates_global_branding(self):
        """POSTing save_settings stores values that immediately flow into every
        template through the school_info context processor."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:change_credentials"),
            {
                "save_settings": "1",
                "school_name": "Al-Noor Public School",
                "school_phone": "0300-1234567",
            },
            follow=True,
        )
        self.assertRedirects(response, reverse("accounts:change_credentials"))
        stored = SchoolSettings.load()
        self.assertEqual(stored.school_name, "Al-Noor Public School")
        self.assertEqual(stored.school_phone, "0300-1234567")

        # Dynamic branding visible on the admin dashboard.
        dash = self.client.get(reverse("core:dashboard"))
        self.assertEqual(dash.status_code, 200)
        self.assertContains(dash, "Al-Noor Public School")

    def test_school_name_required(self):
        """Blank school names are rejected by the model form."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:change_credentials"),
            {
                "save_settings": "1",
                "school_name": "",
                "school_phone": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["settings_form"].errors)
        # Previous (default) branding untouched.
        self.assertEqual(
            SchoolSettings.load().school_name, SchoolSettings.DEFAULT_SCHOOL_NAME
        )

    def test_school_logo_upload_flows_to_templates(self):
        """Uploading a PNG logo persists it under MEDIA_ROOT/school_logo/ and
        exposes it globally so printable headers render the <img> tag."""
        tmp_media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_media, True)

        buffer = io.BytesIO()
        PILImage.new("RGB", (64, 64), color=(20, 90, 160)).save(buffer, format="PNG")
        buffer.seek(0)
        logo = SimpleUploadedFile("crest.png", buffer.read(), content_type="image/png")

        self.client.force_login(self.admin)
        with override_settings(MEDIA_ROOT=tmp_media):
            response = self.client.post(
                reverse("accounts:change_credentials"),
                {
                    "save_settings": "1",
                    "school_name": "Crest Academy",
                    "school_phone": "051-9876543",
                    "school_logo": logo,
                },
                follow=True,
            )
            self.assertRedirects(response, reverse("accounts:change_credentials"))

            stored = SchoolSettings.load()
            self.assertTrue(stored.school_logo)
            self.assertTrue(stored.school_logo.name.startswith("school_logo/"))

            # Context processor now serves the uploaded logo everywhere.
            from apps.core.context_processors import school_info

            info = school_info(request=None)
            self.assertEqual(info["school_logo"].name, stored.school_logo.name)

            # Sidebar brand swaps the emoji for the uploaded logo image.
            dash = self.client.get(reverse("core:dashboard"))
            self.assertEqual(dash.status_code, 200)
            self.assertIn(b"sidebar-brand-logo-img", dash.content)

    def test_print_header_partial_uses_dynamic_branding(self):
        """The shared printable letterhead renders school name + phone."""
        settings_obj = SchoolSettings.load()
        settings_obj.school_name = "Payslip International"
        settings_obj.school_phone = "0999-000111"
        settings_obj.save()

        self.client.force_login(self.admin)
        reports = self.client.get(reverse("core:reports"))
        self.assertEqual(reports.status_code, 200)
        self.assertContains(reports, "Payslip International")
        self.assertContains(reports, "print-brand")


class DashboardAdmissionFeeTests(TestCase):
    """Dashboard admission-fee widget: totals, class filtering, breakdown."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_user",
            password="adminpassword123",
            role=Role.ADMIN,
        )
        self.cls1, _ = SchoolClass.objects.get_or_create(
            name="Class 1", defaults={"order": 4, "monthly_fee": Decimal("1500.00")}
        )
        self.cls2, _ = SchoolClass.objects.get_or_create(
            name="Class 2", defaults={"order": 5, "monthly_fee": Decimal("2000.00")}
        )
        Student.objects.create(
            name="Ali Khan", father_name="Tariq Khan",
            school_class=self.cls1, date_of_birth=date(2015, 5, 12),
            gender=Gender.MALE, is_active=True, admission_fee=Decimal("5000.00"),
        )
        Student.objects.create(
            name="Sara Ahmed", father_name="Ahmed Bilal",
            school_class=self.cls2, date_of_birth=date(2016, 2, 20),
            gender=Gender.FEMALE, is_active=True, admission_fee=Decimal("3000.00"),
        )
        Student.objects.create(
            name="Bilal Raza", father_name="Raza Hassan",
            school_class=self.cls1, date_of_birth=date(2017, 9, 1),
            gender=Gender.MALE, is_active=True,  # no admission fee
        )
        Student.objects.create(
            name="Old Student", father_name="Legacy Parent",
            school_class=self.cls1, date_of_birth=date(2013, 3, 3),
            gender=Gender.MALE, is_active=False, admission_fee=Decimal("9999.00"),
        )

    def _dashboard(self, query=""):
        self.client.force_login(self.admin)
        return self.client.get(reverse("core:dashboard") + query)

    def test_widget_shows_combined_total_for_all_classes(self):
        """All Classes scope sums every active student's admission fee."""
        resp = self._dashboard()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Admission Fees Collected")
        self.assertEqual(resp.context["admission_total"], Decimal("8000.00"))
        self.assertEqual(resp.context["admission_count"], 2)
        self.assertEqual(resp.context["admission_scope_label"], "All Classes")

    def test_class_filter_scopes_admission_totals(self):
        """Selecting a class scopes the total/count/scope-label to it."""
        resp = self._dashboard(f"?class_id={self.cls2.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["admission_total"], Decimal("3000.00"))
        self.assertEqual(resp.context["admission_count"], 1)
        self.assertEqual(resp.context["admission_scope_label"], "Class 2")

    def test_inactive_students_excluded_from_totals(self):
        """The inactive student's 9999 fee never enters the aggregate."""
        resp = self._dashboard()
        self.assertEqual(resp.context["admission_total"], Decimal("8000.00"))

    def test_zero_state_renders_empty_notice(self):
        """With no admission fees recorded the widget shows a friendly notice."""
        Student.objects.update(admission_fee=None)
        resp = self._dashboard()
        self.assertEqual(resp.context["admission_total"], Decimal("0.00"))
        self.assertFalse(resp.context["admission_breakdown"])
        self.assertContains(resp, "No admission fees recorded")

    def test_invalid_class_param_falls_back_to_all_classes(self):
        resp = self._dashboard("?class_id=abc")
        self.assertIsNone(resp.context["selected_class_id"])
        self.assertEqual(resp.context["admission_total"], Decimal("8000.00"))


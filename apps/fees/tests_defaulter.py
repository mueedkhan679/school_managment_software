"""Tests for the Fees Defaulter List Generator feature.

Covers RBAC, class-wise filtering, month-by-month paid/unpaid matrix
correctness, summary counters, and the printable A4 landscape report.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.fees.models import FeeStatus, StudentFee
from apps.fees.views import _build_defaulter_matrix
from apps.students.models import Gender, Student

User = get_user_model()


class DefaulterListTestCase(TestCase):
    """Test suite for the Defaulter List Generator."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_user",
            password="adminpassword123",
            role=Role.ADMIN,
        )
        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="teacherpassword123",
            role=Role.TEACHER,
        )

        # Classes are seeded by data migrations, so get_or_create is required
        # (mirrors apps/fees/tests.py conventions).
        self.cls1, _ = SchoolClass.objects.get_or_create(
            name="Class 1",
            defaults={"order": 1, "monthly_fee": Decimal("1500.00")},
        )
        self.cls1.monthly_fee = Decimal("1500.00")
        self.cls1.save()

        self.playgroup, _ = SchoolClass.objects.get_or_create(
            name="Playgroup",
            defaults={"order": 0, "monthly_fee": Decimal("1000.00")},
        )
        self.playgroup.monthly_fee = Decimal("1000.00")
        self.playgroup.save()

        # stu1: fully paid for 2026 (all 12 months)
        self.stu1 = Student.objects.create(
            name="Ali Khan",
            father_name="Tariq Khan",
            school_class=self.cls1,
            date_of_birth=date(2015, 5, 12),
            gender=Gender.MALE,
            is_active=True,
        )
        # stu2: paid only Jan + Mar 2026 -> defaulter with 10 unpaid months
        self.stu2 = Student.objects.create(
            name="Sara Ahmed",
            father_name="Ahmed Bilal",
            school_class=self.cls1,
            date_of_birth=date(2016, 2, 20),
            gender=Gender.FEMALE,
            is_active=True,
        )
        # stu3: Playgroup, no payments at all -> full defaulter
        self.stu3 = Student.objects.create(
            name="Bilal Raza",
            father_name="Raza Hassan",
            school_class=self.playgroup,
            date_of_birth=date(2017, 9, 1),
            gender=Gender.MALE,
            is_active=True,
        )
        # stu4: inactive student of Class 1 -> must never appear on the report
        self.stu4 = Student.objects.create(
            name="Old Student",
            father_name="Legacy Parent",
            school_class=self.cls1,
            date_of_birth=date(2014, 1, 1),
            gender=Gender.MALE,
            is_active=False,
        )

        for month in range(1, 13):
            StudentFee.objects.create(
                student=self.stu1,
                fee_month=month,
                fee_year=2026,
                amount=Decimal("1500.00"),
                payment_date=date(2026, month, 10),
                status=FeeStatus.PAID,
            )
        for month in (1, 3):
            StudentFee.objects.create(
                student=self.stu2,
                fee_month=month,
                fee_year=2026,
                amount=Decimal("1200.00"),
                payment_date=date(2026, month, 5),
                status=FeeStatus.PAID,
            )

    # ------------------ Access Control ------------------

    def test_anonymous_redirected_from_defaulter_views(self):
        """Unauthenticated requests are redirected to login."""
        for url in (
            reverse("fees:defaulter_list"),
            reverse("fees:defaulter_list_print"),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_forbidden_from_defaulter_views(self):
        """Teachers and students receive 403 Forbidden."""
        self.client.force_login(self.teacher_user)
        for url in (
            reverse("fees:defaulter_list"),
            reverse("fees:defaulter_list_print"),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    # ------------------ Matrix Builder Logic ------------------

    def test_matrix_builder_marks_paid_and_unpaid_months(self):
        """Boolean month array: PAID records -> ✔, everything else -> ✖."""
        rows, summary = _build_defaulter_matrix(
            Student.objects.filter(pk__in=[self.stu1.pk, self.stu2.pk]), 2026
        )
        by_student = {row["student"].pk: row for row in rows}

        row1 = by_student[self.stu1.pk]
        self.assertTrue(all(m["paid"] for m in row1["months"]))
        self.assertEqual(row1["unpaid_count"], 0)

        row2 = by_student[self.stu2.pk]
        paid_flags = {m["num"]: m["paid"] for m in row2["months"]}
        self.assertTrue(paid_flags[1])
        self.assertTrue(paid_flags[3])
        self.assertFalse(paid_flags[2])
        self.assertEqual(row2["unpaid_count"], 10)

    def test_matrix_summary_counts_defaulters_and_cleared(self):
        """Summary aggregates: defaulters = >=1 unpaid month, cleared = 12/12."""
        rows, summary = _build_defaulter_matrix(
            Student.objects.filter(is_active=True), 2026
        )
        self.assertEqual(summary["total_students"], 3)
        self.assertEqual(summary["cleared_count"], 1)   # only stu1
        self.assertEqual(summary["defaulter_count"], 2)  # stu2 + stu3

    def test_matrix_ignores_pending_and_wrong_year_records(self):
        """Only PAID records of the requested year count; PENDING is unpaid."""
        StudentFee.objects.create(
            student=self.stu3,
            fee_month=6,
            fee_year=2026,
            amount=Decimal("1000.00"),
            payment_date=date(2026, 6, 2),
            status=FeeStatus.PENDING,
        )
        StudentFee.objects.create(
            student=self.stu3,
            fee_month=6,
            fee_year=2025,
            amount=Decimal("1000.00"),
            payment_date=date(2025, 6, 2),
            status=FeeStatus.PAID,
        )
        rows, _ = _build_defaulter_matrix(
            Student.objects.filter(pk=self.stu3.pk), 2026
        )
        paid_flags = {m["num"]: m["paid"] for m in rows[0]["months"]}
        self.assertFalse(paid_flags[6])

    # ------------------ View: Screen Report ------------------

    def test_defaulter_list_view_renders_matrix(self):
        """Report renders all active students with tick/cross status glyphs."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("fees:defaulter_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fees/defaulter_list.html")
        self.assertContains(response, "Ali Khan")
        self.assertContains(response, "Sara Ahmed")
        self.assertContains(response, "Bilal Raza")
        self.assertNotContains(response, "Old Student")  # inactive hidden
        self.assertContains(response, "✔")               # paid mark
        self.assertContains(response, "✖")               # unpaid mark
        self.assertEqual(response.context["total_students"], 3)
        self.assertEqual(response.context["defaulter_count"], 2)
        self.assertEqual(response.context["cleared_count"], 1)

    def test_defaulter_list_class_filtering(self):
        """Selecting a class scopes students and summary to that class."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("fees:defaulter_list") + f"?class_id={self.cls1.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_students"], 2)
        self.assertEqual(response.context["scope_label"], "Class 1")
        self.assertContains(response, "Ali Khan")
        self.assertNotContains(response, "Bilal Raza")

    def test_defaulter_list_all_classes_shows_everyone(self):
        """Empty class_id means All Classes."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("fees:defaulter_list"))
        self.assertEqual(response.context["scope_label"], "All Classes")
        self.assertEqual(response.context["total_students"], 3)

    def test_fees_page_contains_generator_button_and_modal(self):
        """Fee Management page exposes the generator button + class modal."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("fees:list"))
        self.assertContains(response, "Generate Defaulter List")
        self.assertContains(response, "defaulter-modal")
        self.assertContains(response, "openDefaulterModal")

    def test_defaulter_list_invalid_class_param_is_ignored(self):
        """Non-numeric / unknown class_id gracefully falls back to All Classes."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("fees:defaulter_list") + "?class_id=abc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["scope_label"], "All Classes")

    # ------------------ View: Print / PDF Report ------------------

    def test_defaulter_print_view_uses_print_template(self):
        """Print endpoint renders the A4 landscape document template."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("fees:defaulter_list_print") + f"?class_id={self.cls1.pk}&year=2026"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fees/defaulter_list_print.html")
        self.assertContains(response, "print-brand-name")   # school name header
        self.assertContains(response, "dl-matrix-table")    # matrix table
        self.assertContains(response, "A4 landscape")       # page setup
        self.assertContains(response, "Defaulters Fee Status Report")
        self.assertEqual(response.context["selected_class"], self.cls1)
        self.assertEqual(response.context["report_year"], 2026)

    def test_defaulter_print_shows_school_branding_context(self):
        """Letterhead branding (school_info context processor) is available."""
        from apps.core.models import SchoolSettings

        settings_obj = SchoolSettings.load()
        settings_obj.school_name = "Iqra Model School"
        settings_obj.school_phone = "03001112233"
        settings_obj.save()

        self.client.force_login(self.admin)
        response = self.client.get(reverse("fees:defaulter_list_print"))
        self.assertContains(response, "Iqra Model School")
        self.assertContains(response, "03001112233")

    def test_defaulter_print_empty_selection_renders_notice(self):
        """A class without students renders an explicit empty-state row."""
        empty_cls, _ = SchoolClass.objects.get_or_create(name="Class 12")
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("fees:defaulter_list_print") + f"?class_id={empty_cls.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_students"], 0)
        self.assertContains(response, "No active students found")
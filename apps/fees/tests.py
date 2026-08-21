from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import Gender, Student

User = get_user_model()


class FeeManagementTestCase(TestCase):
    """Test suite for Phase 6 Student Fee Management system."""

    def setUp(self):
        # Admin user
        self.admin = User.objects.create_user(
            username="admin_user",
            password="adminpassword123",
            role=Role.ADMIN,
        )

        # Teacher user (non-admin)
        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="teacherpassword123",
            role=Role.TEACHER,
        )

        # Classes
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

        # Students
        self.stu1 = Student.objects.create(
            name="Ali Khan",
            father_name="Tariq Khan",
            school_class=self.cls1,
            date_of_birth=date(2015, 5, 12),
            gender=Gender.MALE,
            phone="03001234567",
            is_active=True,
        )
        self.stu2 = Student.objects.create(
            name="Sara Ahmed",
            father_name="Ahmed Bilal",
            school_class=self.cls1,
            date_of_birth=date(2016, 2, 20),
            gender=Gender.FEMALE,
            custom_monthly_fee=Decimal("1200.00"),  # Custom scholarship override
            is_active=True,
        )

        # Existing Fee record
        self.fee1 = StudentFee.objects.create(
            student=self.stu1,
            fee_month=8,
            fee_year=2026,
            amount=Decimal("1500.00"),
            payment_date=date(2026, 8, 10),
            status=FeeStatus.PAID,
            reference="REC-202608-0001",
            recorded_by=self.admin,
        )

    # ------------------ Access Control Tests ------------------

    def test_anonymous_redirected_from_all_fee_views(self):
        """Unauthenticated requests are redirected to login."""
        urls = [
            reverse("fees:list"),
            reverse("fees:create"),
            reverse("fees:voucher", kwargs={"pk": self.fee1.pk}),
            reverse("fees:update", kwargs={"pk": self.fee1.pk}),
            reverse("fees:delete", kwargs={"pk": self.fee1.pk}),
            reverse("fees:api_student_fee_info", kwargs={"student_id": self.stu1.pk}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_forbidden_from_fee_views(self):
        """Non-admin users receive 403 Forbidden."""
        self.client.force_login(self.teacher_user)
        urls = [
            reverse("fees:list"),
            reverse("fees:create"),
            reverse("fees:voucher", kwargs={"pk": self.fee1.pk}),
            reverse("fees:update", kwargs={"pk": self.fee1.pk}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    # ------------------ Fee List & Filter Tests ------------------

    def test_fee_list_view_renders_correctly(self):
        """Fee directory displays transactions and financial metrics."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("fees:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fees/list.html")
        self.assertContains(response, self.fee1.reference)
        self.assertContains(response, self.stu1.name)
        self.assertContains(response, "Rs 1500.00")
        self.assertEqual(response.context["filtered_total"], Decimal("1500.00"))

    def test_fee_list_search_and_filtering(self):
        """Fee list filters by month, year, status, and search query."""
        self.client.force_login(self.admin)

        # Search by student name
        res = self.client.get(reverse("fees:list") + "?q=Ali")
        self.assertContains(res, self.fee1.reference)

        # Search by receipt #
        res = self.client.get(reverse("fees:list") + "?q=REC-202608")
        self.assertContains(res, self.stu1.name)

        # Filter by month and year
        res = self.client.get(reverse("fees:list") + "?month=8&year=2026")
        self.assertContains(res, self.fee1.reference)

        # Filter by non-matching month
        res = self.client.get(reverse("fees:list") + "?month=1&year=2026")
        self.assertNotContains(res, self.fee1.reference)

    # ------------------ Fee Creation & Duplicate Protection Tests ------------------

    def test_create_fee_payment_success(self):
        """Admin can record a valid fee payment and auto-generate receipt."""
        self.client.force_login(self.admin)
        post_data = {
            "student": self.stu2.id,
            "fee_month": 9,
            "fee_year": 2026,
            "amount": "1200.00",
            "payment_date": "2026-09-01",
            "status": "PAID",
            "reference": "",  # Auto-generate
            "is_extra": False,
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 302)

        new_fee = StudentFee.objects.get(student=self.stu2, fee_month=9, fee_year=2026)
        self.assertEqual(new_fee.amount, Decimal("1200.00"))
        self.assertEqual(new_fee.recorded_by, self.admin)
        self.assertTrue(new_fee.reference.startswith("REC-202609-"))

    def test_create_fee_duplicate_protection(self):
        """Duplicate fee entry for same student + month + year without is_extra is blocked."""
        self.client.force_login(self.admin)
        # Attempt duplicate payment for stu1 for August 2026 (already recorded in setUp)
        post_data = {
            "student": self.stu1.id,
            "fee_month": 8,
            "fee_year": 2026,
            "amount": "1500.00",
            "payment_date": "2026-08-15",
            "status": "PAID",
            "is_extra": False,
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("already been recorded", str(response.context["form"].errors))

    def test_create_fee_with_is_extra_allowed(self):
        """Duplicate fee entry for same student + month + year with is_extra=True is permitted."""
        self.client.force_login(self.admin)
        post_data = {
            "student": self.stu1.id,
            "fee_month": 8,
            "fee_year": 2026,
            "amount": "300.00",
            "payment_date": "2026-08-20",
            "status": "PAID",
            "reference": "REC-LATE-01",
            "is_extra": True,
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            StudentFee.objects.filter(student=self.stu1, fee_month=8, fee_year=2026).count(),
            2,
        )

    def test_create_fee_rejects_negative_or_zero_amount(self):
        """Amounts <= 0 are rejected by validation."""
        self.client.force_login(self.admin)
        post_data = {
            "student": self.stu2.id,
            "fee_month": 10,
            "fee_year": 2026,
            "amount": "0.00",
            "payment_date": "2026-10-01",
            "status": "PAID",
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    # ------------------ Voucher & Update & Delete Tests ------------------

    def test_fee_voucher_view(self):
        """Fee voucher view displays student details, receipt #, and annual financial balance."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("fees:voucher", kwargs={"pk": self.fee1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "fees/voucher.html")
        self.assertContains(response, self.fee1.reference)
        self.assertContains(response, self.stu1.name)
        self.assertEqual(response.context["current_year_paid"], Decimal("1500.00"))
        # Yearly expected for stu1 = 1500 * 12 = 18000. Remaining = 18000 - 1500 = 16500
        self.assertEqual(response.context["yearly_pending"], Decimal("16500.00"))

    def test_fee_update(self):
        """Admin can edit an existing fee transaction."""
        self.client.force_login(self.admin)
        update_data = {
            "student": self.stu1.id,
            "fee_month": 8,
            "fee_year": 2026,
            "amount": "1600.00",
            "payment_date": "2026-08-11",
            "status": "PAID",
            "reference": "REC-UPDATED-1",
            "is_extra": False,
        }
        response = self.client.post(
            reverse("fees:update", kwargs={"pk": self.fee1.pk}),
            data=update_data,
        )
        self.assertEqual(response.status_code, 302)
        self.fee1.refresh_from_db()
        self.assertEqual(self.fee1.amount, Decimal("1600.00"))
        self.assertEqual(self.fee1.reference, "REC-UPDATED-1")

    def test_fee_delete(self):
        """Admin can delete a fee payment record."""
        self.client.force_login(self.admin)
        response = self.client.post(reverse("fees:delete", kwargs={"pk": self.fee1.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StudentFee.objects.filter(pk=self.fee1.pk).exists())

    def test_api_student_fee_info(self):
        """API returns student effective fee and paid months list for dynamic form pre-filling."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("fees:api_student_fee_info", kwargs={"student_id": self.stu1.id}) + "?year=2026"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["student_id"], self.stu1.student_id)
        self.assertEqual(data["effective_monthly_fee"], 1500.0)
        self.assertIn(8, data["paid_months"])

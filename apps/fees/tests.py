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

    def test_fee_delete_nonexistent_record_redirects_with_flash(self):
        """Deleting a non-existent fee redirects to the list with an error flash, not 404."""
        self.client.force_login(self.admin)
        missing_pk = self.fee1.pk + 100
        response = self.client.post(reverse("fees:delete", kwargs={"pk": missing_pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("fees:list"))
        listing = self.client.get(response.url)
        self.assertContains(listing, f"Fee record #{missing_pk}")
        self.assertContains(listing, "was not found")

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

    # ------------------ Multi-Month Fee Collection & Lock Guard Tests ------------------

    def test_create_multi_month_fee_payment_success(self):
        """Admin can collect multiple months in a single transaction."""
        self.client.force_login(self.admin)
        # stu2 has effective monthly fee of 1200.00
        # Collect for months 1, 2, 3 at total 3600.00
        post_data = {
            "student": self.stu2.id,
            "fee_months": [1, 2, 3],
            "fee_year": 2026,
            "amount": "3600.00",
            "payment_date": "2026-01-10",
            "status": "PAID",
            "reference": "",
            "is_extra": False,
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 302)

        created = StudentFee.objects.filter(student=self.stu2, fee_year=2026).order_by("fee_month")
        self.assertEqual(created.count(), 3)
        self.assertEqual(list(created.values_list("fee_month", flat=True)), [1, 2, 3])
        for f in created:
            self.assertEqual(f.amount, Decimal("1200.00"))
            self.assertEqual(f.status, FeeStatus.PAID)
            self.assertEqual(f.school_class, self.stu2.school_class)
            self.assertEqual(f.session_year, self.stu2.current_session)
            self.assertEqual(f.recorded_by, self.admin)
        # Verify single combined reference shared across all 3 records
        refs = set(created.values_list("reference", flat=True))
        self.assertEqual(len(refs), 1)

    def test_create_multi_month_fee_duplicate_protection(self):
        """Selecting an already-paid month in multi-month collection raises validation error."""
        self.client.force_login(self.admin)
        # stu1 already has month 8 paid
        post_data = {
            "student": self.stu1.id,
            "fee_months": [8, 9, 10],
            "fee_year": 2026,
            "amount": "4500.00",
            "payment_date": "2026-09-10",
            "status": "PAID",
            "is_extra": False,
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("already been recorded", str(response.context["form"].errors))

    def test_create_multi_month_fee_lock_guard_exceeding_12_months(self):
        """Total paid months for current session cannot exceed 12."""
        self.client.force_login(self.admin)
        # stu1 already has month 8 paid (1 month). Pay 10 more months (months 1-7, 9-11)
        for m in [1, 2, 3, 4, 5, 6, 7, 9, 10, 11]:
            StudentFee.objects.create(
                student=self.stu1,
                school_class=self.cls1,
                session_year=self.stu1.current_session,
                fee_month=m,
                fee_year=2026,
                amount=Decimal("1500.00"),
                payment_date=date(2026, m, 1),
                status=FeeStatus.PAID,
            )
        # stu1 now has 11 months paid for session. Attempting to collect 2 months (e.g. 12 and something else)
        # should exceed the 12-month limit (11 + 2 = 13 > 12)
        post_data = {
            "student": self.stu1.id,
            "fee_months": [12, 1],  # 2 months
            "fee_year": 2026,
            "amount": "3000.00",
            "payment_date": "2026-12-01",
            "status": "PAID",
            "is_extra": False,
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertTrue(
            "exceeds the 12-month session limit" in str(response.context["form"].errors)
            or "already completed all 12 months" in str(response.context["form"].errors)
            or "already been recorded" in str(response.context["form"].errors)
        )

    def test_voucher_displays_all_combined_months(self):
        """Combined voucher displays all months paid under the shared reference."""
        self.client.force_login(self.admin)
        post_data = {
            "student": self.stu2.id,
            "fee_months": [4, 5],
            "fee_year": 2026,
            "amount": "2400.00",
            "payment_date": "2026-04-10",
            "status": "PAID",
            "reference": "REC-COMBINED-001",
            "is_extra": False,
        }
        response = self.client.post(reverse("fees:create"), data=post_data)
        self.assertEqual(response.status_code, 302)

        created = StudentFee.objects.filter(student=self.stu2, reference="REC-COMBINED-001")
        first_fee = created.first()
        voucher_res = self.client.get(reverse("fees:voucher", kwargs={"pk": first_fee.pk}))
        self.assertEqual(voucher_res.status_code, 200)
        self.assertContains(voucher_res, "REC-COMBINED-001")
        self.assertContains(voucher_res, "April 2026")
        self.assertContains(voucher_res, "May 2026")
        self.assertEqual(voucher_res.context["total_voucher_amount"], Decimal("2400.00"))


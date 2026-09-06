"""Tests for the refined Student Promotion & Fee Clearance workflow.

Covers the strict 12-month fee lock, the admin student-page clearance
badge + active Promote button, the Target-Class promotion page, academic
history archiving, and the 0/12 tracker reset on promotion.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.fees.forms import StudentFeeForm
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import (
    MONTHS_PER_SESSION,
    Gender,
    Student,
    StudentAcademicHistory,
)

User = get_user_model()


class PromotionWorkflowTestCase(TestCase):
    """End-to-end promotion/fee-clearance workflow tests."""

    SESSION_YEAR = "2025-2026"

    def setUp(self):
        self.admin = User.objects.create_user(
            username="promo_admin",
            password="adminpass123",
            role=Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.cls9, _ = SchoolClass.objects.get_or_create(
            name="Class 9", defaults={"order": 9, "monthly_fee": Decimal("1500.00")}
        )
        self.cls10, _ = SchoolClass.objects.get_or_create(
            name="Class 10", defaults={"order": 10, "monthly_fee": Decimal("2000.00")}
        )
        self.student = Student.objects.create(
            name="Ahmed Raza",
            father_name="Raza Ali",
            school_class=self.cls9,
            date_of_birth=date(2010, 3, 15),
            gender=Gender.MALE,
            is_active=True,
        )
        self.client.force_login(self.admin)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_fee(self, month, year, student=None, **extra):
        return StudentFee.objects.create(
            student=student or self.student,
            school_class=self.cls9,
            fee_month=month,
            fee_year=year,
            session_year=self.SESSION_YEAR,
            amount=Decimal("1500.00"),
            payment_date=date(year, (month % 12) + 1, 5),
            status=FeeStatus.PAID,
            **extra,
        )

    def _pay_all_session_months(self):
        for month in range(1, 13):
            fee_year = 2025 if month <= 6 else 2026
            self._create_fee(month, fee_year)

    def _pay_some_months(self, count=3):
        for month in range(1, count + 1):
            fee_year = 2025 if month <= 6 else 2026
            self._create_fee(month, fee_year)
# ------------------------------------------------------------------
    # Model: session tracker & clearance
    # ------------------------------------------------------------------
    def test_tracker_counts_distinct_paid_months_only(self):
        self.assertEqual(self.student.paid_months_count, 0)
        self.assertFalse(self.student.is_fee_cleared)
        # A PENDING record must NOT count toward clearance.
        StudentFee.objects.create(
            student=self.student,
            school_class=self.cls9,
            fee_month=1,
            fee_year=2025,
            session_year=self.SESSION_YEAR,
            amount=Decimal("1500.00"),
            payment_date=date(2025, 2, 5),
            status=FeeStatus.PENDING,
        )
        self.assertEqual(self.student.paid_months_count, 0)

        self._create_fee(2, 2025)
        self.assertEqual(self.student.paid_months_count, 1)
        self.assertEqual(self.student.fee_clearance_status, "1/12 Months Paid")

    def test_is_fee_cleared_at_12_months_with_highlight_label(self):
        self._pay_all_session_months()
        self.assertEqual(self.student.paid_months_count, MONTHS_PER_SESSION)
        self.assertTrue(self.student.is_fee_cleared)
        self.assertEqual(self.student.fee_clearance_status, "12/12 Months Cleared")
        self.assertEqual(self.student.current_session, self.SESSION_YEAR)

    def test_session_lock_blocks_new_monthly_fee_at_model_level(self):
        self._pay_all_session_months()
        # Monthly fee (month 7, fee_year 2025) is not a duplicate, but the
        # 2025-2026 session is already 12/12 cleared -> must lock.
        with self.assertRaises(ValidationError):
            self._create_fee(7, 2025)

    def test_session_lock_allows_extra_payment(self):
        self._pay_all_session_months()
        # Extra payments (late fee / exam fee) stay allowed after the lock.
        extra = self._create_fee(1, 2025, is_extra=True)
        self.assertIsNotNone(extra.pk)

    def test_session_lock_does_not_break_editing_existing_records(self):
        self._pay_all_session_months()
        first = StudentFee.objects.filter(student=self.student).order_by("id").first()
        first.reference = "REC-FIXED-0001"
        first.save()  # must not raise despite the session being locked
        first.refresh_from_db()
        self.assertEqual(first.reference, "REC-FIXED-0001")

    def test_lock_does_not_block_new_fees_for_a_different_session(self):
        self._pay_all_session_months()
        # A fresh 2026-2027 session in the same class starts at 0/12.
        fee = StudentFee.objects.create(
            student=self.student,
            school_class=self.cls9,
            fee_month=1,
            fee_year=2026,
            session_year="2026-2027",
            amount=Decimal("1500.00"),
            payment_date=date(2026, 2, 5),
            status=FeeStatus.PAID,
        )
        self.assertIsNotNone(fee.pk)
# ------------------------------------------------------------------
    # Fee form & collection view: friendly lock feedback
    # ------------------------------------------------------------------
    def test_fee_form_rejects_locked_session(self):
        self._pay_all_session_months()
        form = StudentFeeForm(
            data={
                "student": self.student.pk,
                "fee_month": 7,
                "fee_year": 2025,
                "amount": "1500.00",
                "payment_date": "2025-07-10",
                "status": FeeStatus.PAID,
                "reference": "",
                "is_extra": False,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("locked", str(form.errors))

    def test_fee_form_allows_extra_payment_when_locked(self):
        self._pay_all_session_months()
        form = StudentFeeForm(
            data={
                "student": self.student.pk,
                "fee_month": 7,
                "fee_year": 2025,
                "amount": "1500.00",
                "payment_date": "2025-07-10",
                "status": FeeStatus.PAID,
                "reference": "",
                "is_extra": True,
            }
        )
        self.assertTrue(form.is_valid())

    def test_fee_collection_view_blocks_locked_session(self):
        self._pay_all_session_months()
        response = self.client.post(
            reverse("fees:create"),
            {
                "student": self.student.pk,
                "fee_month": 7,
                "fee_year": 2025,
                "amount": "1500.00",
                "payment_date": "2025-07-10",
                "status": FeeStatus.PAID,
                "reference": "",
            },
        )
        # Invalid form -> re-rendered with the lock error message.
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "locked")
# ------------------------------------------------------------------
    # Admin student page: clearance badge + active Promote button
    # ------------------------------------------------------------------
    def test_admin_change_page_highlights_clearance_and_promote_button(self):
        self._pay_all_session_months()
        response = self.client.get(
            reverse("admin:students_student_change", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        clearance = response.context["fee_clearance"]
        self.assertTrue(clearance["is_cleared"])
        self.assertEqual(clearance["paid_count"], MONTHS_PER_SESSION)
        self.assertEqual(clearance["session_year"], self.SESSION_YEAR)
        self.assertContains(response, "12/12 Months Cleared")
        self.assertContains(response, "Promote Student")
        self.assertContains(
            response, reverse("admin:students_student_promote", args=[self.student.pk])
        )

    def test_admin_change_page_does_not_offer_promote_before_clearance(self):
        self._pay_some_months(3)
        response = self.client.get(
            reverse("admin:students_student_change", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["fee_clearance"]["is_cleared"])
        self.assertNotContains(response, "Promote Student")
# ------------------------------------------------------------------
    # Per-student Target-Class promotion workflow
    # ------------------------------------------------------------------
    def test_admin_promote_page_renders_target_class_dropdown(self):
        self._pay_all_session_months()
        response = self.client.get(
            reverse("admin:students_student_promote", args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Target Class")
        # Available classes are listed; the current class is excluded.
        self.assertContains(response, f'value="{self.cls10.pk}"')
        self.assertNotContains(response, f'value="{self.cls9.pk}"')

    def test_admin_promote_post_archives_and_promotes(self):
        self._pay_all_session_months()
        response = self.client.post(
            reverse("admin:students_student_promote", args=[self.student.pk]),
            {
                "apply": "1",
                "new_class": str(self.cls10.pk),
                "_selected_action": self.student.pk,
            },
        )
        expected_redirect = reverse(
            "admin:students_student_change", args=[self.student.pk]
        )
        self.assertRedirects(response, expected_redirect)

        self.student.refresh_from_db()
        self.assertEqual(self.student.school_class, self.cls10)
        self.assertEqual(self.student.status, "PROMOTED")
        # A permanent archive row captures the finished session.
        archived = StudentAcademicHistory.objects.get(student=self.student)
        self.assertEqual(archived.school_class, self.cls9)
        self.assertEqual(archived.session_year, self.SESSION_YEAR)
        self.assertEqual(archived.fee_clearance_status, "12/12 Months Cleared")
        self.assertEqual(archived.status_tag, "PROMOTED")
        # Tracker reset: 0/12 for the new class/session.
        self.assertEqual(self.student.paid_months_count, 0)
        self.assertFalse(self.student.is_fee_cleared)

    def test_admin_promote_blocks_incomplete_fees_without_override(self):
        self._pay_some_months(3)
        response = self.client.post(
            reverse("admin:students_student_promote", args=[self.student.pk]),
            {"apply": "1", "new_class": str(self.cls10.pk)},
        )
        self.assertEqual(response.status_code, 302)  # back to the promote page
        self.student.refresh_from_db()
        self.assertEqual(self.student.school_class, self.cls9)
        self.assertFalse(
            StudentAcademicHistory.objects.filter(student=self.student).exists()
        )

        # Now try again WITH the override -> forced promotion succeeds.
        response = self.client.post(
            reverse("admin:students_student_promote", args=[self.student.pk]),
            {
                "apply": "1",
                "new_class": str(self.cls10.pk),
                "allow_incomplete_fees": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.school_class, self.cls10)
        self.assertEqual(self.student.status, "PROMOTED")
        archived = StudentAcademicHistory.objects.get(student=self.student)
        self.assertEqual(archived.fee_clearance_status, "3/12 Months Paid")

    def test_promote_to_rejects_same_class(self):
        self._pay_all_session_months()
        with self.assertRaises(ValidationError):
            self.student.promote_to(self.cls9)

# ------------------------------------------------------------------
    # Bulk promotion action
    # ------------------------------------------------------------------
    def test_bulk_promote_intermediate_renders_target_class_dropdown(self):
        self._pay_all_session_months()
        # Triggering the action WITHOUT "apply" renders the confirmation step
        # featuring the Target Class dropdown.
        response = self.client.post(
            reverse("admin:students_student_changelist"),
            {
                "action": "promote_students",
                "select_across": "0",
                "index": "0",
                "_selected_action": self.student.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Target Class")
        self.assertContains(response, f'value="{self.cls10.pk}"')
        self.assertContains(response, "12/12 Months Cleared")
    # ------------------------------------------------------------------
    # Bulk promotion action
    # ------------------------------------------------------------------
    def test_bulk_promote_action(self):
        self._pay_all_session_months()
        response = self.client.post(
            reverse("admin:students_student_changelist"),
            {
                "action": "promote_students",
                "select_across": "0",
                "index": "0",
                "_selected_action": self.student.pk,
                "new_class": str(self.cls10.pk),
                "apply": "1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.school_class, self.cls10)
        self.assertEqual(self.student.status, "PROMOTED")
        self.assertTrue(
            StudentAcademicHistory.objects.filter(student=self.student).exists()
        )
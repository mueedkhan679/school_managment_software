"""Tests for the auto-absent logic and the mark_auto_absent command."""

from datetime import date, datetime
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Role
from apps.teachers.models import Teacher, TeacherAttendance

from django.contrib.auth import get_user_model

User = get_user_model()


class AutoAbsentHelperTests(TestCase):
    """Tests for apps.teachers.auto_absent helpers + management command."""

    def setUp(self):
        # Teacher present today
        self.t_present = Teacher.objects.create(
            name="Present Teacher", phone="03000000001",
            monthly_salary=Decimal("30000.00"), is_active=True,
        )
        TeacherAttendance.objects.create(
            teacher=self.t_present, date=timezone.localdate(),
            time_in=datetime.strptime("08:00", "%H:%M").time(),
            status="PRESENT", source="QR",
        )
        # Teacher on leave today
        self.t_leave = Teacher.objects.create(
            name="Leave Teacher", phone="03000000002",
            monthly_salary=Decimal("30000.00"), is_active=True,
        )
        TeacherAttendance.objects.create(
            teacher=self.t_leave, date=timezone.localdate(),
            status="LEAVE", source="MANUAL",
        )
        # Teacher with NO entry today -> should be auto-absent
        self.t_missing = Teacher.objects.create(
            name="Missing Teacher", phone="03000000003",
            monthly_salary=Decimal("30000.00"), is_active=True,
        )
        # Inactive teacher -> must NEVER be auto-marked
        self.t_inactive = Teacher.objects.create(
            name="Inactive Teacher", phone="03000000004",
            monthly_salary=Decimal("30000.00"), is_active=False,
        )

    def test_mark_auto_absent_marks_only_missing_active(self):
        from apps.teachers.auto_absent import mark_auto_absent

        created = mark_auto_absent(force=True)
        self.assertEqual(created, 1)
        rec = TeacherAttendance.objects.get(teacher=self.t_missing)
        self.assertEqual(rec.status, "ABSENT")
        self.assertEqual(rec.source, "AUTO")
        self.assertIsNone(rec.time_in)
        # Present/Leave/inactive users unaffected; no duplicates
        self.assertEqual(
            TeacherAttendance.objects.filter(date=timezone.localdate()).count(), 3
        )
        self.assertFalse(
            TeacherAttendance.objects.filter(teacher=self.t_inactive).exists()
        )

    def test_mark_auto_absent_does_not_create_duplicate(self):
        from apps.teachers.auto_absent import mark_auto_absent

        mark_auto_absent(force=True)
        second = mark_auto_absent(force=True)
        self.assertEqual(second, 0)  # no one left missing
        self.assertEqual(
            TeacherAttendance.objects.filter(
                teacher=self.t_missing
            ).count(), 1
        )

    def test_command_with_force_marks_absent(self):
        call_command("mark_auto_absent", "--force")
        self.assertTrue(
            TeacherAttendance.objects.filter(
                teacher=self.t_missing, status="ABSENT", source="AUTO"
            ).exists()
        )

    def test_command_with_date_marks_that_day(self):
        # A past date is always considered closed, so no --force needed.
        past = timezone.localdate()
        fake_date = date(2020, 1, 5)
        call_command("mark_auto_absent", "--date", fake_date.isoformat())
        self.assertTrue(
            TeacherAttendance.objects.filter(
                teacher=self.t_missing, date=fake_date, status="ABSENT", source="AUTO"
            ).exists()
        )
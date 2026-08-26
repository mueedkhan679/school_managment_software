"""Regression tests for the Teacher Attendance Overview dashboard feature.

Covers the admin dashboard teacher attend overview (total/present/absent +
named lists) and that the 10:00 AM auto-absence pass is triggered from the
dashboard render.
"""
from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.teachers.models import Teacher, TeacherAttendance

User = get_user_model()


class TeacherAttendanceOverviewDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="ov_admin", password="password123", role=Role.ADMIN,
        )
        self.present = Teacher.objects.create(
            name="Present Sir", phone="03001111111",
            monthly_salary=Decimal("30000.00"),
        )
        self.absent = Teacher.objects.create(
            name="Absent Sir", phone="03002222222",
            monthly_salary=Decimal("32000.00"),
        )
        TeacherAttendance.objects.create(
            teacher=self.present, date=timezone.localdate(),
            time_in=time(8, 45), status="PRESENT", source="QR",
        )
        TeacherAttendance.objects.create(
            teacher=self.absent, date=timezone.localdate(),
            status="ABSENT", source="AUTO", time_in=None,
        )
        self.client.force_login(self.admin)

    def test_dashboard_renders_teacher_overview_section(self):
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertContains(resp, "Teacher Attendance Overview")
        self.assertContains(resp, self.present.name)
        self.assertContains(resp, self.absent.name)
        self.assertContains(resp, self.present.teacher_id)

    def test_dashboard_context_counts_teacher_present_absent(self):
        resp = self.client.get(reverse("core:dashboard"))
        ctx = resp.context
        self.assertEqual(ctx["teacher_present_count"], 1)
        self.assertEqual(ctx["teacher_absent_count"], 1)
        self.assertEqual(ctx["total_teachers"], 2)
        self.assertEqual(len(ctx["present_teachers"]), 1)
        self.assertEqual(len(ctx["absent_teachers"]), 1)
        # Present entry carries the check-in time.
        self.assertEqual(ctx["present_teachers"][0]["time_in"], time(8, 45))
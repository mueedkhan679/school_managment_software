"""Regression tests: teacher creation survives a stale/lagging Sequence counter.

Root cause fixed here: ``Teacher.save()`` claimed ``TCH-XXXXXX`` IDs from the
monotonic ``Sequence`` counter without any collision recovery. When the counter
row was missing or lagging behind existing rows (database restore/import,
manual edits, seeded data), every registration attempt crashed with an unhandled
``IntegrityError: UNIQUE constraint failed: teachers_teacher.teacher_id``
(a raw HTTP 500 for the admin). The model now detects collisions, re-syncs the
counter past the conflicting number, and retries with a fresh ID.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.core.models import Sequence
from apps.teachers.models import Teacher

User = get_user_model()


class SequenceEnsureAboveTests(TestCase):
    """Unit tests for the Sequence.ensure_above() helper."""

    def test_bumps_lagging_counter_forward(self):
        Sequence.objects.create(name="teacher", next_value=1)
        Sequence.ensure_above("teacher", 5)
        self.assertEqual(Sequence.objects.get(name="teacher").next_value, 6)

    def test_never_moves_counter_backwards(self):
        Sequence.objects.create(name="teacher", next_value=6)
        Sequence.ensure_above("teacher", 2)
        self.assertEqual(Sequence.objects.get(name="teacher").next_value, 6)

    def test_missing_row_is_created_on_demand(self):
        self.assertFalse(Sequence.objects.filter(name="teacher").exists())
        Sequence.ensure_above("teacher", 9)
        self.assertEqual(Sequence.objects.get(name="teacher").next_value, 10)


class TeacherCreationSelfHealingTests(TestCase):
    """End-to-end registration via the view must tolerate a drifted counter."""

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            username="heal_admin", password="password123", role=Role.ADMIN,
        )
        self.cls = SchoolClass.objects.create(
            name="Heal Class", order=1, monthly_fee=Decimal("1500.00"),
        )

    def _post_teacher(self, name):
        self.client.force_login(self.admin)
        return self.client.post(reverse("teachers:create"), {
            "name": name,
            "phone": "03001234567",
            "monthly_salary": "40000.00",
            "address": "Lahore",
            "assigned_classes": [str(self.cls.id)],
        })

    def test_missing_counter_row_self_heals_during_registration(self):
        """Simulates a restored DB where the counter row is absent entirely."""
        existing = Teacher.objects.create(
            name="Existing Sir", phone="03009998877",
            monthly_salary=Decimal("30000.00"),
        )
        existing_num = int(existing.teacher_id.split("-")[1])
        Sequence.objects.filter(name="teacher").delete()

        response = self._post_teacher("Fresh Teacher")

        self.assertEqual(response.status_code, 302)
        fresh = Teacher.objects.get(name="Fresh Teacher")
        self.assertTrue(fresh.teacher_id.startswith("TCH-"))
        self.assertNotEqual(fresh.teacher_id, existing.teacher_id)
        self.assertGreater(
            int(fresh.teacher_id.split("-")[1]),
            existing_num,
            "Generated ID must land past every existing teacher number.",
        )

    def test_colliding_counter_resyncs_and_creates_successfully(self):
        """Counter pointing exactly at an occupied number self-corrects."""
        occupied = Teacher.objects.create(
            name="Occupied Sir", phone="03008887777",
            monthly_salary=Decimal("28000.00"),
        )
        occupied_num = int(occupied.teacher_id.split("-")[1])
        Sequence.objects.update_or_create(
            name="teacher", defaults={"next_value": occupied_num}
        )

        response = self._post_teacher("Collision Survivor")

        self.assertEqual(response.status_code, 302)
        fresh = Teacher.objects.get(name="Collision Survivor")
        self.assertNotEqual(fresh.teacher_id, occupied.teacher_id)
        self.assertGreater(int(fresh.teacher_id.split("-")[1]), occupied_num)
        # Counter itself must have been pushed past the collision.
        self.assertGreater(
            Sequence.objects.get(name="teacher").next_value, occupied_num
        )


class TeacherAccountLinkingTests(TestCase):
    """Linking a login account must assign Role.TEACHER and connect profiles."""

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            username="link_admin", password="password123", role=Role.ADMIN,
        )
        self.teacher = Teacher.objects.create(
            name="Linked Teacher", phone="03005556666",
            monthly_salary=Decimal("25000.00"),
        )

    def test_link_assigns_teacher_role_and_connects_profile(self):
        self.client.force_login(self.admin)
        res = self.client.post(reverse("accounts:account_create"), {
            "profile_type": "teacher",
            "profile_id": str(self.teacher.id),
            "username": "tch_linked",
            "password1": "Str0ngPass!23",
            "password2": "Str0ngPass!23",
        })
        self.assertEqual(res.status_code, 302)
        self.teacher.refresh_from_db()
        self.assertIsNotNone(self.teacher.user_id)
        self.assertEqual(self.teacher.user.role, Role.TEACHER)
        self.assertTrue(self.teacher.user.is_active)

    def test_duplicate_username_is_blocked_without_crashing(self):
        """Case-variant duplicate usernames are rejected by form validation."""
        User.objects.create_user(username="taken_user", password="password123", role=Role.STUDENT)
        self.client.force_login(self.admin)
        res = self.client.post(reverse("accounts:account_create"), {
            "profile_type": "teacher",
            "profile_id": str(self.teacher.id),
            "username": "TAKEN_USER",
            "password1": "Str0ngPass!23",
            "password2": "Str0ngPass!23",
        })
        self.assertEqual(res.status_code, 302)  # redirected back with an error message
        self.teacher.refresh_from_db()
        self.assertIsNone(self.teacher.user_id)  # no link created for rejected form
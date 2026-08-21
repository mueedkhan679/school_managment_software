"""Comprehensive test suite for Phase 10: User Account Management & Printable ID Cards."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.students.models import Gender, Student
from apps.teachers.models import Teacher

User = get_user_model()


class Phase10AccountManagementTestCase(TestCase):
    """Tests for /accounts/manage/ — User account CRUD and status management."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_phase10",
            password="adminpassword123",
            role=Role.ADMIN,
        )
        self.non_admin = User.objects.create_user(
            username="teacher_phase10",
            password="teacherpassword123",
            role=Role.TEACHER,
        )
        self.cls, _ = SchoolClass.objects.get_or_create(
            name="Class 1",
            defaults={"order": 1, "monthly_fee": Decimal("1500.00")},
        )
        # Active student without a linked account
        self.student = Student.objects.create(
            name="Ayesha Siddiqui",
            father_name="Khalid Siddiqui",
            school_class=self.cls,
            date_of_birth=date(2014, 3, 10),
            gender=Gender.FEMALE,
            is_active=True,
        )
        # Active teacher without a linked account
        self.teacher = Teacher.objects.create(
            name="Sir Bilal",
            phone="03009876543",
            monthly_salary=Decimal("35000.00"),
            is_active=True,
        )

    # ---- Access Control ----

    def test_anonymous_redirected(self):
        """Anonymous requests to account management redirect to login."""
        res = self.client.get(reverse("accounts:account_list"))
        self.assertEqual(res.status_code, 302)
        self.assertIn(reverse("accounts:login"), res.url)

    def test_non_admin_forbidden(self):
        """Non-admin users receive HTTP 403 on all account management views."""
        self.client.force_login(self.non_admin)
        urls = [
            reverse("accounts:account_list"),
            reverse("accounts:id_card_batch_students"),
            reverse("accounts:id_card_batch_teachers"),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 403, f"Expected 403 for {url}")

    # ---- Account List View ----

    def test_account_list_renders(self):
        """Account management list page renders successfully for admin."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse("accounts:account_list"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "accounts/account_list.html")
        ctx = res.context
        self.assertIn("students_without_account", ctx)
        self.assertIn("teachers_without_account", ctx)
        self.assertIn(self.student, ctx["students_without_account"])
        self.assertIn(self.teacher, ctx["teachers_without_account"])

    # ---- Create Account for Student ----

    def test_create_student_account_success(self):
        """Admin can create and link a login account to a student."""
        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("accounts:account_create"),
            {
                "profile_type": "student",
                "profile_id": str(self.student.id),
                "username": "stu_phase10",
                "password1": "TestP@ssw0rd!",
                "password2": "TestP@ssw0rd!",
            },
        )
        self.assertEqual(res.status_code, 302)
        self.student.refresh_from_db()
        self.assertIsNotNone(self.student.user_id)
        self.assertEqual(self.student.user.role, Role.STUDENT)
        self.assertEqual(self.student.user.username, "stu_phase10")
        self.assertTrue(self.student.user.is_active)

    # ---- Create Account for Teacher ----

    def test_create_teacher_account_success(self):
        """Admin can create and link a login account to a teacher."""
        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("accounts:account_create"),
            {
                "profile_type": "teacher",
                "profile_id": str(self.teacher.id),
                "username": "tch_phase10",
                "password1": "TestP@ssw0rd!",
                "password2": "TestP@ssw0rd!",
            },
        )
        self.assertEqual(res.status_code, 302)
        self.teacher.refresh_from_db()
        self.assertIsNotNone(self.teacher.user_id)
        self.assertEqual(self.teacher.user.role, Role.TEACHER)
        self.assertEqual(self.teacher.user.username, "tch_phase10")

    # ---- Unique Username Enforcement ----

    def test_create_duplicate_username_blocked(self):
        """Accounts with duplicate usernames are rejected at form level."""
        User.objects.create_user(username="existing_user", password="pass", role=Role.STUDENT)
        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("accounts:account_create"),
            {
                "profile_type": "student",
                "profile_id": str(self.student.id),
                "username": "existing_user",
                "password1": "TestP@ssw0rd!",
                "password2": "TestP@ssw0rd!",
            },
        )
        self.assertEqual(res.status_code, 302)
        # Student should still have no account (form rejected)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.user_id)

    # ---- Toggle Account Status ----

    def test_toggle_account_status_disable_and_activate(self):
        """Admin can disable and re-activate a student/teacher account."""
        user_acc = User.objects.create_user(
            username="toggle_user", password="TestP@ssw0rd!", role=Role.STUDENT
        )
        self.student.user = user_acc
        self.student.save()

        self.client.force_login(self.admin)

        # Disable
        res = self.client.post(
            reverse("accounts:account_toggle_status", kwargs={"user_id": user_acc.id})
        )
        self.assertEqual(res.status_code, 302)
        user_acc.refresh_from_db()
        self.assertFalse(user_acc.is_active)

        # Re-activate
        res = self.client.post(
            reverse("accounts:account_toggle_status", kwargs={"user_id": user_acc.id})
        )
        self.assertEqual(res.status_code, 302)
        user_acc.refresh_from_db()
        self.assertTrue(user_acc.is_active)

    # ---- Password Reset ----

    def test_admin_password_reset_view_renders(self):
        """Password reset view renders for an existing student/teacher account."""
        user_acc = User.objects.create_user(
            username="resetme_user", password="OldP@ssword1", role=Role.STUDENT
        )
        self.student.user = user_acc
        self.student.save()

        self.client.force_login(self.admin)
        res = self.client.get(
            reverse("accounts:account_reset_password", kwargs={"user_id": user_acc.id})
        )
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "accounts/reset_password.html")
        self.assertEqual(res.context["account_user"], user_acc)

    def test_admin_password_reset_updates_password(self):
        """Admin password reset successfully updates the user's hashed password."""
        user_acc = User.objects.create_user(
            username="changepw_user", password="OldP@ssword1", role=Role.TEACHER
        )
        self.teacher.user = user_acc
        self.teacher.save()

        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("accounts:account_reset_password", kwargs={"user_id": user_acc.id}),
            {
                "new_password1": "NewP@ssw0rd!",
                "new_password2": "NewP@ssw0rd!",
            },
        )
        self.assertEqual(res.status_code, 302)
        user_acc.refresh_from_db()
        self.assertTrue(user_acc.check_password("NewP@ssw0rd!"))

    # ---- Account Deletion ----

    def test_account_delete_unlinks_profile(self):
        """Deleting a user account removes the user but keeps the student profile."""
        user_acc = User.objects.create_user(
            username="delete_me", password="TestP@ssw0rd!", role=Role.STUDENT
        )
        self.student.user = user_acc
        self.student.save()
        user_id = user_acc.id

        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("accounts:account_delete", kwargs={"user_id": user_id})
        )
        self.assertEqual(res.status_code, 302)
        self.assertFalse(User.objects.filter(id=user_id).exists())
        # Profile still exists, just unlinked
        self.student.refresh_from_db()
        self.assertIsNone(self.student.user_id)

    # ---- Admin Account Toggle Protection ----

    def test_admin_account_cannot_be_toggled(self):
        """Admin role accounts cannot be toggled via account_toggle_status (returns 404)."""
        another_admin = User.objects.create_user(
            username="another_admin", password="pass", role=Role.ADMIN
        )
        self.client.force_login(self.admin)
        res = self.client.post(
            reverse("accounts:account_toggle_status", kwargs={"user_id": another_admin.id})
        )
        self.assertEqual(res.status_code, 404)


class Phase10IDCardTestCase(TestCase):
    """Tests for printable ID card views."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_idcards",
            password="adminpassword123",
            role=Role.ADMIN,
        )
        self.cls, _ = SchoolClass.objects.get_or_create(
            name="Class 1",
            defaults={"order": 1, "monthly_fee": Decimal("1500.00")},
        )
        self.student = Student.objects.create(
            name="Zara Malik",
            father_name="Nadeem Malik",
            school_class=self.cls,
            date_of_birth=date(2013, 7, 22),
            gender=Gender.FEMALE,
            is_active=True,
        )
        self.teacher = Teacher.objects.create(
            name="Madam Nadia",
            phone="03001234567",
            monthly_salary=Decimal("40000.00"),
            is_active=True,
        )
        self.teacher.assigned_classes.add(self.cls)

    def test_individual_student_id_card(self):
        """Individual student ID card renders the student's details."""
        self.client.force_login(self.admin)
        res = self.client.get(
            reverse("accounts:id_card_student", kwargs={"student_id": self.student.student_id})
        )
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "accounts/id_card_student.html")
        self.assertContains(res, self.student.name)
        self.assertContains(res, self.student.student_id)
        self.assertContains(res, self.student.father_name)

    def test_individual_teacher_id_card(self):
        """Individual teacher ID card renders the teacher's details."""
        self.client.force_login(self.admin)
        res = self.client.get(
            reverse("accounts:id_card_teacher", kwargs={"teacher_id": self.teacher.teacher_id})
        )
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "accounts/id_card_teacher.html")
        self.assertContains(res, self.teacher.name)
        self.assertContains(res, self.teacher.teacher_id)

    def test_batch_student_id_cards_all_classes(self):
        """Batch student ID card view renders all active students."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse("accounts:id_card_batch_students"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "accounts/id_card_student.html")
        self.assertContains(res, self.student.student_id)

    def test_batch_student_id_cards_class_filter(self):
        """Batch student ID card view respects class_id filter."""
        self.client.force_login(self.admin)
        res = self.client.get(
            reverse("accounts:id_card_batch_students") + f"?class_id={self.cls.id}"
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, self.student.student_id)

    def test_batch_teacher_id_cards(self):
        """Batch teacher ID card view renders all active teachers."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse("accounts:id_card_batch_teachers"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "accounts/id_card_teacher.html")
        self.assertContains(res, self.teacher.teacher_id)

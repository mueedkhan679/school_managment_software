from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role

User = get_user_model()


def make_admin(username="admin", password="admin123", **kwargs):
    """Create (or recreate) an admin user.

    The test database is built by running all migrations - including the data
    migration that seeds the ``admin`` user - so we remove any pre-existing row
    for the same username before creating. TestCase transactions roll back this
    change between tests.
    """
    defaults = {"role": Role.ADMIN, "is_staff": True, "is_superuser": True}
    defaults.update(kwargs)
    User.objects.filter(username=username).delete()
    return User.objects.create_user(username=username, password=password, **defaults)


class LoginViewTests(TestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_login_page_contains_csrf_token(self):
        resp = self.client.get(reverse("accounts:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "csrfmiddlewaretoken")

    def test_login_page_renders_expected_markup(self):
        resp = self.client.get(reverse("accounts:login"))
        self.assertContains(resp, 'name="username"')
        self.assertContains(resp, 'name="password"')

    def test_login_success_redirects_to_dashboard(self):
        resp = self.client.post(
            reverse("accounts:login"), {"username": "admin", "password": "admin123"}
        )
        self.assertRedirects(resp, reverse("core:dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.admin.pk)

    def test_login_invalid_credentials_shows_error(self):
        resp = self.client.post(
            reverse("accounts:login"), {"username": "admin", "password": "wrong-password"}
        )
        self.assertContains(resp, "Invalid username or password")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_unknown_user_shows_invalid_credentials(self):
        resp = self.client.post(
            reverse("accounts:login"), {"username": "ghost", "password": "whatever"}
        )
        self.assertContains(resp, "Invalid username or password")

    def test_login_disabled_account_shows_disabled_message(self):
        make_admin(username="locked", password="pwabc12345", is_active=False)
        resp = self.client.post(
            reverse("accounts:login"), {"username": "locked", "password": "pwabc12345"}
        )
        self.assertContains(resp, "disabled")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_teacher_and_student_role_redirects(self):
        from decimal import Decimal
        from datetime import date
        from apps.teachers.models import Teacher
        from apps.students.models import Student
        from apps.classrooms.models import SchoolClass

        sc = SchoolClass.objects.first()
        t_user = User.objects.create_user(username="teacher1", password="pwabc12345", role=Role.TEACHER)
        Teacher.objects.create(name="Teacher One", phone="03001234567", monthly_salary=Decimal("40000.00"), user=t_user)

        resp = self.client.post(
            reverse("accounts:login"), {"username": "teacher1", "password": "pwabc12345"}
        )
        self.assertRedirects(resp, reverse("teacher_portal:dashboard"))

        self.client.logout()
        s_user = User.objects.create_user(username="student1", password="pwabc12345", role=Role.STUDENT)
        Student.objects.create(name="Student One", father_name="Father", school_class=sc, date_of_birth=date(2010, 1, 1), gender="M", user=s_user)

        resp2 = self.client.post(
            reverse("accounts:login"), {"username": "student1", "password": "pwabc12345"}
        )
        self.assertRedirects(resp2, reverse("student_portal:dashboard"))

    def test_next_parameter_is_respected(self):
        target = reverse("core:dashboard")
        resp = self.client.post(
            f"{reverse('accounts:login')}?next={quote(target)}",
            {"username": "admin", "password": "admin123", "next": target},
        )
        self.assertRedirects(resp, target)

    def test_open_redirect_is_blocked(self):
        resp = self.client.post(
            f"{reverse('accounts:login')}?next=https://evil.example.com",
            {"username": "admin", "password": "admin123", "next": "https://evil.example.com"},
        )
        self.assertRedirects(resp, reverse("core:dashboard"))

    def test_session_key_rotates_on_login(self):
        self.client.get(reverse("accounts:login"))
        before = self.client.session.session_key
        self.client.post(
            reverse("accounts:login"), {"username": "admin", "password": "admin123"}
        )
        after = self.client.session.session_key
        self.assertIsNotNone(before)
        self.assertNotEqual(before, after)

    def test_authenticated_admin_visiting_login_redirects_to_dashboard(self):
        self.client.login(username="admin", password="admin123")
        resp = self.client.get(reverse("accounts:login"))
        self.assertRedirects(resp, reverse("core:dashboard"))


class AccessControlTests(TestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_anonymous_redirected_to_login_with_next(self):
        target = reverse("core:dashboard")
        resp = self.client.get(target)
        self.assertRedirects(resp, f"{reverse('accounts:login')}?next={quote(target, safe='')}")

    def test_non_admin_gets_403(self):
        User.objects.create_user(username="teacher1", password="pwabc12345", role=Role.TEACHER)
        self.client.login(username="teacher1", password="pwabc12345")
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_dashboard(self):
        self.client.login(username="admin", password="admin123")
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dashboard")

    def test_index_redirects_anonymous_to_login(self):
        resp = self.client.get(reverse("core:index"))
        self.assertRedirects(resp, reverse("accounts:login"))


class LogoutTests(TestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_logout_get_is_rejected(self):
        self.client.login(username="admin", password="admin123")
        resp = self.client.get(reverse("accounts:logout"))
        self.assertEqual(resp.status_code, 405)

    def test_logout_post_flushes_session_and_redirects(self):
        self.client.login(username="admin", password="admin123")
        self.assertIn("_auth_user_id", self.client.session)
        resp = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(resp, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_protected_page_redirects_after_logout(self):
        self.client.login(username="admin", password="admin123")
        self.client.post(reverse("accounts:logout"))
        resp = self.client.get(reverse("core:dashboard"))
        self.assertRedirects(resp, f"{reverse('accounts:login')}?next={quote(reverse('core:dashboard'), safe='')}")


class ChangeCredentialsTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.login(username="admin", password="admin123")

    def test_change_username_and_password_success(self):
        resp = self.client.post(
            reverse("accounts:change_credentials"),
            {
                "current_password": "admin123",
                "username": "superadmin",
                "new_password1": "New@Secure2026!",
                "new_password2": "New@Secure2026!",
            },
        )
        self.assertRedirects(resp, reverse("core:dashboard"))

        updated = User.objects.get(pk=self.admin.pk)
        self.assertEqual(updated.username, "superadmin")
        self.assertTrue(updated.check_password("New@Secure2026!"))
        # The password is stored hashed, never as plain text.
        self.assertNotEqual(updated.password, "New@Secure2026!")
        self.assertNotIn("New@Secure2026!", updated.password)

        # Session remains valid after the change (not logged out).
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)

        # Old credentials no longer work; new ones do.
        self.client.logout()
        self.assertFalse(self.client.login(username="admin", password="admin123"))
        self.assertTrue(self.client.login(username="superadmin", password="New@Secure2026!"))

    def test_wrong_current_password_rejected(self):
        resp = self.client.post(
            reverse("accounts:change_credentials"),
            {
                "current_password": "wrong-password",
                "username": "hacker",
                "new_password1": "",
                "new_password2": "",
            },
        )
        self.assertContains(resp, "incorrect")
        self.assertEqual(User.objects.get(pk=self.admin.pk).username, "admin")

    def test_password_mismatch_rejected(self):
        resp = self.client.post(
            reverse("accounts:change_credentials"),
            {
                "current_password": "admin123",
                "username": "admin",
                "new_password1": "BrandNewPass1!",
                "new_password2": "DifferentPass1!",
            },
        )
        self.assertIn("new_password2", resp.context["form"].errors)
        self.assertIn(
            "The two password fields didn't match.", resp.context["form"].errors["new_password2"]
        )
        self.assertTrue(User.objects.get(pk=self.admin.pk).check_password("admin123"))

    def test_weak_password_rejected(self):
        resp = self.client.post(
            reverse("accounts:change_credentials"),
            {
                "current_password": "admin123",
                "username": "admin",
                "new_password1": "password",
                "new_password2": "password",
            },
        )
        # "password" is rejected by Django's CommonPasswordValidator.
        self.assertContains(resp, "password")
        self.assertTrue(User.objects.get(pk=self.admin.pk).check_password("admin123"))

    def test_duplicate_username_rejected(self):
        make_admin(username="other")
        resp = self.client.post(
            reverse("accounts:change_credentials"),
            {
                "current_password": "admin123",
                "username": "other",
                "new_password1": "",
                "new_password2": "",
            },
        )
        self.assertContains(resp, "already in use")
        self.assertEqual(User.objects.get(pk=self.admin.pk).username, "admin")

    def test_unauthorized_user_cannot_access_page(self):
        User.objects.create_user(username="teacher1", password="pwabc12345", role=Role.TEACHER)
        self.client.login(username="teacher1", password="pwabc12345")
        resp = self.client.get(reverse("accounts:change_credentials"))
        self.assertEqual(resp.status_code, 403)




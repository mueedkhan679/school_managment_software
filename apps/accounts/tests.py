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


class LoginUITests(TestCase):
    """Login page redesign: demo credentials removed, modern UI, remember me."""

    def setUp(self):
        self.admin = make_admin()

    def test_login_page_has_no_demo_credentials(self):
        """The demo credentials helper card/text is completely gone."""
        resp = self.client.get(reverse("accounts:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Default credentials")
        self.assertNotContains(resp, "admin123")

    def test_login_page_style_block_is_wellformed(self):
        """Regression: all CSS lives inside ONE properly-closed <style> tag."""
        resp = self.client.get(reverse("accounts:login"))
        html = resp.content.decode()
        self.assertEqual(html.count("<style>"), 1)
        self.assertEqual(html.count("</style>"), 1)
        start = html.index("<style>")
        end = html.index("</style>")
        # Button/spinner CSS must be INSIDE the style block...
        self.assertIn(".btn-signin", html[start:end])
        self.assertIn(".lgi-row", html[start:end])
        # ...and no raw CSS may leak into the document after it closes.
        self.assertNotIn(".lgi-", html[end:])

    def test_login_page_contains_modern_ui_elements(self):
        """Branding, password toggle, remember-me checkbox and loading state exist."""
        from apps.core.models import SchoolSettings

        SchoolSettings.objects.update_or_create(
            pk=1, defaults={"school_name": "Iqra Model School"}
        )
        resp = self.client.get(reverse("accounts:login"))
        self.assertContains(resp, "togglePassword")      # show/hide toggle
        self.assertContains(resp, 'name="remember_me"')  # remember checkbox
        self.assertContains(resp, "login-brand-logo")    # dynamic branding block
        self.assertContains(resp, "Iqra Model School")   # school name from settings
        self.assertContains(resp, "Signing In")          # button loading label

    def test_remember_me_keeps_session_for_two_weeks(self):
        from apps.accounts.views import REMEMBER_ME_SECONDS

        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "admin123", "remember_me": "on"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.session.get_expiry_age(), REMEMBER_ME_SECONDS)

    def test_without_remember_me_session_expires_on_browser_close(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"username": "admin", "password": "admin123"},
        )
        self.assertEqual(resp.status_code, 302)
        # get_expiry_age() falls back to SESSION_COOKIE_AGE when the stored
        # expiry is 0, so browser-close semantics are checked explicitly.
        self.assertTrue(self.client.session.get_expire_at_browser_close())


class SidebarLogoutButtonTests(TestCase):
    """Dashboard layout exposes an accessible POST-based logout button."""

    def setUp(self):
        self.admin = make_admin()

    def test_dashboard_shows_post_logout_button(self):
        self.client.login(username="admin", password="admin123")
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)
        logout_url = reverse("accounts:logout")
        self.assertContains(resp, f'action="{logout_url}"')
        self.assertContains(resp, "sidebar-user-logout")

    def test_logout_button_posts_and_redirects_to_login(self):
        """End-to-end: pressing the sidebar button logs the user out."""
        self.client.login(username="admin", password="admin123")
        resp = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(resp, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)



